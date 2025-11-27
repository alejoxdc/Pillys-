# -*- coding: utf-8 -*-
import subprocess
import os
import glob
import time
import logging
import shutil

import odoo
from time import strftime
from odoo import models

_logger = logging.getLogger("############### Backup ODOO DB Logs #################")


class OdooBackuplocal(models.Model):
    """
    Base CLass for Backup Configuration
    """
    _inherit = 'auto.backup'

    def copy_filestore(self, db, filestore_path, dirr, x_days):
        """
        Copies Filestore recursively to the defined location.
        :param db: Current DB
        :param filestore_path: filestore location
        :param dirr: backup path
        :param x_days: X old days to remove files
        :return:
        """
        x_days_ago = self.calc_x_days(x_days)
        thetime = str(strftime("%Y-%m-%d-%H-%M-%S"))
        name = os.path.join(dirr, 'filestore' + '_' + thetime)
        filestore_path = os.path.join(filestore_path, db)
        filestore = filestore_path if os.path.exists(filestore_path) else odoo.tools.config.filestore(db)
        self._check_path_access(dirr)
        self._check_path_access(filestore)

        self.log("Filestore Backup Started...............")

        # Delete Older Files, < Days Specified in conf
        self.log("Looking Old filestore backup files to remove...")
        try:
            glob_list = glob.glob(os.path.join(dirr, 'filestore') + '*')
            for file in glob_list:
                file_info = os.stat(file)
                if file_info.st_ctime < x_days_ago:
                    self.log("Filestore Unlink: %s" % file)
                    os.unlink(file)
                else:
                    self.log("Filestore Keeping : %s" % file)
            self.log("Filestore Backup files older than %s deleted." % time.strftime('%c', time.gmtime(x_days_ago)))
        except Exception as e:
            self.log("Looking Old Filestore backup files to remove....Failed", "Exception")
            self.message_post(
                body="Filestore Backup Unlink Error.\n Info: %s" % (str(e) or repr(e)),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")

        # Backup Filestore
        try:
            if os.path.exists(filestore):  # If Path Exists?
                os.makedirs(name)  # Create a new path for backup
                zipfile = shutil._make_zipfile(base_name=name, base_dir=filestore)  # Zip Recursively filestore
                shutil.rmtree(name)  # Remove the temp dir
                self.log("Filestore Backup Done ..............%s" % zipfile)
                self.message_post(
                    body="FileStore Backup Success.\n Path: " + os.path.join(dirr, 'filestore' + '_' + thetime),
                    subtype_xmlid="mail.mt_comment",
                    message_type="comment")
        except Exception as e:
            self.log("Filestore Backup Failed......... %s" % ("File exists" + dirr + '/filestore/'), type='exception')
            self.message_post(
                body="File exists" + dirr + '/filestore/ \n Info: %s' % (str(e) or repr(e)),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
            return False
        self.log("Filestore Backup Done...............")

    # Dump DB
    def dump_start(self, db, user, password, host, dirr, dumper, x_days):
        """
        Function DUMP Database from postgres db pool to the defined location.
        :param db: Current Database to DUMP
        :param user: Database USER from odoo-server-config
        :param password: Password USER from odoo-server-config
        :param host: host in default localhost, will get host from odoo-server-config
        :param dirr: Path to dump Database
        :param dumper: PSQL Query to DUMP according to the format c,t,p
        :param x_days: Interval to remove old backups.
        :return: False if error.
        """
        USER = user.strip()
        PASS = password.strip()
        HOST = host.strip()
        BACKUP_DIR = dirr.strip() if dirr.strip()[-1] == '/' else dirr.strip() + '/'
        dumper = dumper
        x_days = x_days or 1
        database_list = []

        self._check_path_access(dirr)

        # Change the value in brackets to keep more/fewer files. time.time() returns seconds since 1970...
        # currently set to 2 days ago from when this script starts to run.

        x_days_ago = self.calc_x_days(x_days)

        os.putenv('PGPASSWORD', PASS)

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
                glob_list = glob.glob(BACKUP_DIR + database_name + '*')
                for file in glob_list:
                    file_info = os.stat(file)
                    if file_info.st_ctime < x_days_ago:
                        self.log("Unlink: %s" % file)
                        os.unlink(file)
                    else:
                        self.log("Keeping : %s" % file)

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
                if dumper != 'with filestore':
                    # Run the pg_dump command to the right directory
                    command = dumper.format(db_name=database_name.strip(),
                                            b_db_name=BACKUP_DIR.strip() + file_name.strip(),
                                            user=USER, host=HOST.strip())
                    self.log(command)
                    subprocess.call(command, shell=True)
                else:
                    filepath = os.path.join(BACKUP_DIR.strip(), file_name.strip())
                    with open(filepath, "wb") as f:
                        odoo.service.db.dump_db(database_name.strip(), f)
                self.log("%s dump finished" % database_name)
                self.log("Backup job complete.")
                self.message_post(
                    body="Backup Completed.",
                    subtype_xmlid="mail.mt_comment",
                    message_type="comment")
                return True
        except Exception as e:
            self.log(e, "Exception")
            self.message_post(
                body="Backup Error.\n Info: %s" % (str(e) or repr(e)),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
        raise Exception
