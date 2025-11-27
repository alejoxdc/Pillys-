# -*- coding: utf-8 -*-
import subprocess
import os
import time
import logging
import shutil
import tempfile
import pysftp

import odoo
from time import strftime
from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger("############### Backup ODOO DB - SFTP Logs #################")

cnopts = pysftp.CnOpts()
cnopts.hostkeys = None  # Disable host key checking for simplicity (not recommended for production)

class OdooBackupServer(models.Model):
    """
    Base CLass for remote file backup transfer
    """
    _inherit = 'auto.backup'

    # Remote Server Fields
    remote_host = fields.Char(string='Remote Host',
                              size=100,
                              copy=False,
                              default='/',
                              tracking=True)
    remote_user = fields.Char(string='SFTP User',
                              size=100,
                              copy=False,
                              default='root')
    remote_password = fields.Char(string="SFTP User Password",
                                  copy=False, )

    def test_sftp(self):
        """
        Testing SFTP connection
        :return:
        """
        for record in self:
            try:
                pysftp.Connection(host=record.remote_host, username=record.remote_user, password=record.remote_password, cnopts=cnopts)
            except Exception:
                raise UserError('Connection Failed ...!')
            title = _("Connection Test Succeeded!")
            message = _("Everything seems properly set up!")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': title,
                    'message': message,
                    'sticky': False,
                }
            }

    def remote_transfer_filestore(self, db, filestore_path, remote_host, remote_user, remote_pswd, dirr, x_days):
        """
        Copy Filestore from local path to remote server
        :param db: Current DB
        :param filestore_path: Local Filestore Path - Default from ODOO Config
        :param remote_host: host ip
        :param remote_user: remote user
        :param remote_pswd: Credentials
        :param dirr: Backup Path In Remote
        :param x_days: x days to remove old files
        :return:
        """
        x_days_ago = self.calc_x_days(x_days)
        thetime = str(strftime("%Y-%m-%d-%H-%M-%S"))
        filestore_path = os.path.join(filestore_path, db)
        filestore = filestore_path if os.path.exists(filestore_path) else odoo.tools.config.filestore(db)
        BACKUP_DIR = dirr.strip() if dirr.strip()[-1] == '/' else dirr.strip() + '/'
        R_HOST = remote_host.strip()
        R_USER = remote_user.strip()
        R_PASS = remote_pswd.strip()

        self._check_path_access(filestore)

        self.log("Filestore Backup Started...............")

        try:
            sftp = pysftp.Connection(host=R_HOST, username=R_USER, password=R_PASS, cnopts=cnopts)
            self.log("SFTP Connection Established ...........#")
        except Exception as e:
            self.log("SFTP Connection Failed ...........#")
            self.message_post(
                body="SFTP Connection Failed.\n Info: %s" % (str(e) or repr(e)),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
            return

        # Delete Older Files, < Days Specified in conf
        self.log("Looking Old filestore backup files to remove...")
        try:
            try:
                with sftp.cd(BACKUP_DIR):  # Change the current working directory
                    glob_list = sftp.listdir_attr()  # Listing the files in remote path
                    for file in glob_list:
                        if file.st_mtime < x_days_ago and 'filestore' in file.filename and sftp.isfile(
                                os.path.join(BACKUP_DIR + file.filename)):
                            sftp.remove(os.path.join(BACKUP_DIR + file.filename))  # Unlinking old backups
                            self.log("Filestore  Unlink...................: %s" % file.filename)
                        #     # os.unlink(file)
                        else:
                            self.log("Keeping................. : %s" % file.filename)
            except Exception as e:
                self.log("Accessing Files Error %s" % (str(e) or repr(e)), type='Exception')
            self.log("Filestore Backup files older than %s deleted." % time.strftime('%c', time.gmtime(x_days_ago)))
        except Exception as e:
            self.log("Looking Old Filestore backup files to remove....Failed", "Exception")
            self.message_post(
                body="Filestore Backup Unlink Error.\n Info: %s" % (str(e) or repr(e)),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")

        # Backup Filestore
        dump_dir = tempfile.mkdtemp()
        name = os.path.join(dump_dir, 'filestore' + '_' + thetime)
        try:
            if os.path.exists(filestore):  # If Path Exists?
                zipfile = shutil._make_zipfile(base_name=name,
                                               base_dir=filestore)  # Zip Recursively filestore in base_dir path
                sftp.put_d(dump_dir, dirr)  # Copying the Tempdir/TempBackupfile -> Remote Dir
                self.log("Filestore Backup Done ..............%s -> %s" % (zipfile, filestore))
                self.message_post(
                    body="FileStore Backup Success.\n Path: " + os.path.join(dirr, 'filestore' + '_' + thetime),
                    subtype_xmlid="mail.mt_comment",
                    message_type="comment")
        except Exception as e:
            self.log("Filestore Backup Failed......... %s" % ("File exists" + dirr + '/filestore/'), type='exception')
            self.message_post(
                body="Filestore Backup Exception: %s" % (str(e) or repr(e)),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
        finally:
            sftp.close()
            self.log("SFTP Connection Closing.......")
            shutil.rmtree(dump_dir)
            self.log("Temp File & Dir Unlinked.......")
        self.log("Filestore Backup Done...............")

    def remote_dump_start(self, db, user, password, host, remote_host, remote_user, remote_pswd, dirr, dumper, x_days):
        """
        Function DUMP Database from postgres db pool to remote dir.
        :param db: Current Database to DUMP
        :param user: Database USER from odoo-server-config
        :param password: Password USER from odoo-server-config
        :param host: host in default localhost, will get host from odoo-server-config
        :param remote_host: SFTP HOST
        :param remote_pswd: SFTP PASSORWD
        :param remote_user: SFTP USER
        :param dirr: Path to dump Database
        :param dumper: PSQL Query to DUMP according to the format c,t,p
        :param x_days: Interval to remove old backups.
        :return: False if error.
        """
        USER = user.strip()
        PASS = password.strip()
        HOST = host.strip()
        R_HOST = remote_host.strip()
        R_USER = remote_user.strip()
        R_PASS = remote_pswd.strip()
        BACKUP_DIR = dirr.strip() if dirr.strip()[-1] == '/' else dirr.strip() + '/'
        dumper = dumper
        dump_dir = ''
        x_days = x_days or 1
        database_list = []

        # Change the value in brackets to keep more/fewer files. time.time() returns seconds since 1970...
        # currently set to 2 days ago from when this script starts to run.
        x_days_ago = self.calc_x_days(x_days)
        os.putenv('PGPASSWORD', PASS)

        try:
            sftp = pysftp.Connection(host=R_HOST, username=R_USER, password=R_PASS, cnopts=cnopts)
            self.log("SFTP Connection Established ...........#")
        except Exception as e:
            self.log("SFTP Connection Failed ...........#")
            self.message_post(
                body="SFTP Connection Failed.\n Info: %s" % (str(e) or repr(e)),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
            return

        self.log("Starting Job...............")
        try:
            database_list = subprocess.Popen(
                'echo select datname from pg_database | psql -t -U %s -h %s template1' % (USER, HOST), shell=True,
                stdout=subprocess.PIPE).stdout.readlines()
            self.log("Reading Database.......................%s" % database_list)
        except Exception as e:
            self.log("Reading Database.......................Failed", "Exception")
            self.message_post(
                body="Backup Error.\n Info: %s" % (str(e) or repr(e)),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")

        # Delete old backup files first.
        self.log("Looking Old backup files to remove...")
        try:
            for database_name in database_list:
                if isinstance(database_name, bytes):  # database name will be bytes of type.so need to decode
                    database_name = database_name.decode('utf-8')
                database_name = database_name.strip()
                if database_name != db.strip():
                    continue
                # glob_list = glob.glob(BACKUP_DIR + database_name + '*')
                try:
                    with sftp.cd(BACKUP_DIR):  # Change the current working directory
                        glob_list = sftp.listdir_attr()  # Listing the files in remote path
                        for file in glob_list:
                            if file.st_mtime < x_days_ago and database_name in file.filename and sftp.isfile(
                                    os.path.join(BACKUP_DIR + file.filename)):
                                sftp.remove(os.path.join(BACKUP_DIR + file.filename))  # Unlinking old backups
                                self.log("Unlink...................: %s" % file.filename)
                            #     # os.unlink(file)
                            else:
                                self.log("Keeping................. : %s" % file.filename)
                except Exception as e:
                    self.log("Accessing Files Error %s" % (str(e) or repr(e)), type='Exception')
            self.log("Backup files older than %s deleted." % time.strftime('%c', time.gmtime(x_days_ago)))
        except Exception as e:
            self.log("Looking Old backup files to remove....Failed", "Exception")
            self.message_post(
                body="Backup Unlink Error.\n Info: %s" % (str(e) or repr(e)),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")

        try:
            # Now perform the backup.
            for database_name in database_list:
                if isinstance(database_name, bytes):  # database name will be bytes of type.so need to decode
                    database_name = database_name.decode('utf-8')
                if str(database_name).strip() != db.strip():
                    continue
                self.log("dump started for %s" % database_name)
                thetime = str(strftime("%Y-%m-%d-%H-%M"))
                file_name = database_name.strip() + '_' + thetime
                # Run the pg_dump command to the right directory
                dump_dir = tempfile.mkdtemp()
                if dumper != 'with filestore':
                    if dump_dir:
                        dirpath = os.path.join(dump_dir, file_name.strip())
                        command = dumper.format(db_name=database_name.strip(), b_db_name=dirpath,
                                                user=USER, host=HOST.strip())
                        self.log(command)
                        subprocess.call(command, shell=True)
                else:
                    filepath = os.path.join(dump_dir, file_name.strip())
                    with open(filepath, "wb") as f:
                        odoo.service.db.dump_db(database_name.strip(), f)
                if dump_dir or filepath:
                    sftp.put_d(dump_dir, dirr)  # Copying the Tempdir/TempBackupfile -> Remote Dir
                    self.log("%s dump finished" % database_name)
                    self.log("Backup job complete.")
                    self.message_post(
                        body="Backup Completed.",
                        subtype_xmlid="mail.mt_comment",
                        message_type="comment")
        except Exception as e:
            self.log(e, "Exception")
            self.message_post(
                body="Backup Error.\n Info: %s" % (str(e) or repr(e)),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
        finally:
            sftp.close()
            self.log("SFTP Connection Closing.......")
            shutil.rmtree(dump_dir)
            self.log("Temp File & Dir Unlinked.......")
        # raise Exception
