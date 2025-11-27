# -*- coding: utf-8 -*-
import glob
import json
import simplejson
import logging
import os
import shutil
import subprocess
import tempfile
from time import strftime
import datetime
import time
import requests
import dropbox

from tqdm import tqdm

import odoo
from odoo import models, fields, api
from werkzeug.urls import url_encode

_logger = logging.getLogger("############### Backup ODOO DB To Dropbox Logs #################")


class OdooBackupDropbox(models.Model):
    """
    Base CLass for Backup DB To Dropbox
    """
    _inherit = 'auto.backup'

    @api.depends('backup_mode')
    def _get_dropbox_authentication_url(self):
        """

        :return: URL To Authenticate APP With Dropbox
        """
        for record in self:
            if record.backup_mode == 'dropbox':
                base_uri = 'https://www.dropbox.com/oauth2/authorize'
                data = {
                    'client_id': 'nivzp0j2rp97cyq',
                    # For test purpose, we can use localhost.
                    # 'redirect_uri': '%s/dropbox/authentication' % self.env['ir.config_parameter'].sudo().get_param(
                    #     'web.base.url', default='localhost:8069'),
                    # since we don't know the url in production, User must copy the code to Dropbox backup record
                    # from dropbox response
                    'response_type': 'code'
                }
                print(base_uri, data)
                record.dropbox_uri = "%s?%s&force_reapprove=true" % (base_uri, url_encode(data))
            else:
                record.dropbox_uri = False

    def _get_dropbox_access_tocken(self, code):
        """
        Getting Access token from the given access code
        :param code:
        :return:
        """
        url = "https://api.dropboxapi.com/oauth2/token"
        params = {
            'code': code,
            'grant_type': 'authorization_code'
        }
        payload = {}
        stream = 'bml2enAwajJycDk3Y3lxOmo4ejByc2F4N3E4YTJ2cA=='
        headers = {
            'Authorization': 'Basic %s' % stream
        }

        response = requests.request("POST", url, headers=headers, data=payload, params=params)

        if response.status_code == 200:
            response = simplejson.loads(response.text.encode('utf8'))
            return "access_token" in response and response.get('access_token')
        elif response.status_code in [400, 401]:
            self.message_post(body="DropBox Authorization Code Expired.\n Please Generate Again. Info: %s" % (
                    str(response.text.encode('utf8')) or repr(response.text.encode('utf8'))),
                              subtype_xmlid="mail.mt_comment",
                              message_type="comment")

    @api.model
    def set_all_tokens(self, code):
        """

        :param code:
        :return:
        """
        dropbox_backups = self.env['auto.backup'].search([('backup_mode', '=', 'dropbox')])
        dropbox_backups.write({'dropbox_secret': code})
        action = self.env.ref('auto_backup_odoo.action_auto_backup_odoo_config')
        menu = self.env.ref('auto_backup_odoo.menu_auto_backup_db_psql_config')
        return '/web#id=%s&action=%s&model=auto.backup&view_type=form&cids=&menu_id=%s' % (
            dropbox_backups[0].id, action.id, menu.id)

    # dropbox_redirect_uri
    dropbox_uri = fields.Char(string='Redirect URI',
                              copy=False,
                              compute='_get_dropbox_authentication_url', store=True)
    dropbox_key = fields.Char(string='Client Key', )
    dropbox_secret = fields.Char(string='Generated Key',
                                 copy=False)
    dropbox_token = fields.Char(string='Generated Access Token',
                                copy=False,
                                readonly=1)

    @api.onchange('dropbox_secret')
    def onchange_dropbox_secret(self):
        """
        Reset Access Token Whenever the Access key is changed.
        :return:
        """
        for record in self:
            if record.backup_mode == 'dropbox':
                record.dropbox_token = False

    # Remove the fetched files
    def remove_batch(self, token, fetched_files):
        """
        Remove the fetched files as a batch.
        :param token: Token for authentication
        :param fetched_files: [list of files]
        :return:
        """
        url = "https://api.dropboxapi.com/2/files/delete_batch"

        payload = {
            "entries": fetched_files
        }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % token,
        }

        response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
        # We don't need to check the asynchronous status.
        if response.status_code == 200:
            self.log("Dropbox File Unlink Success %s" % fetched_files)
            self.message_post(
                body="Unlink Success. Info: File",
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
            return True
        else:
            self.log("Drive File Unlink Filed. Info: %s" % (response.text.encode('utf8')))
            self.message_post(
                body="Unlink Failed. Info: %s" % (response.text.encode('utf8')),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
            return False

    # Fetch files from the specified path
    def fetch_files(self, token, path, x_days, database_name, cursor=False):
        """
        fetch files in a dir to compare and remove from path, according to the x days to remove.
        :param token: Token for authentication
        :param path: Path in dropbox to list data.
        :param cursor:
        :return:
        """
        fetched_files = []

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % token,
        }
        if not cursor:
            url = "https://api.dropboxapi.com/2/files/list_folder"
            payload = {
                "path": "%s" % path,
                "recursive": False,
                "include_deleted": False,
                "include_has_explicit_shared_members": False,
                "include_mounted_folders": True,
                "include_non_downloadable_files": True
            }
        else:
            url = "https://api.dropboxapi.com/2/files/list_folder/continue"
            payload = {
                "cursor": cursor
            }
        response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            data = simplejson.loads(response.text.encode('utf8'))
            # client_modified is iso format
            # Format '2020-05-28T10:39:01Z'
            fetched_files.extend([{"path": file_id['path_display']} for file_id in data['entries']
                                  if time.mktime(
                    datetime.datetime.strptime(file_id['client_modified'],
                                               "%Y-%m-%dT%H:%M:%SZ").timetuple()) < x_days and file_id[
                                      'name'] in database_name])
            # has_more flag indicates pagination.
            # If set, we need to fetch the by same request with the cursor from previous response.
            if data['has_more']:
                self.fetch_files(token, path, x_days, cursor=data['cursor'])
            else:
                return fetched_files
        else:
            self.message_post(body="File Lookup Failed. Info: %s" % (response.text.encode('utf8')),
                              subtype_xmlid="mail.mt_comment",
                              message_type="comment")
            return []

    # Upload data in a session.
    def session_upload(self, token, file, path, file_name):
        """
        Append files in the session that we created. Session can hold 350gb of files.
        :param token: Access Tocken To Access the Dropbox.
        :param session_id: Started Session to continue upload
        :param file: File to upload
        :param offset: data offset left to upload.
        :return: False / Response status code
        """
        dbx = dropbox.Dropbox(token, timeout=900)
        target_path = os.path.join(path, file_name.strip())
        metadata = False
        with open(file, "rb") as f:
            file_size = os.path.getsize(file)
            chunk_size = 4 * 1024 * 1024
            if file_size <= chunk_size:
                print(dbx.files_upload(f.read(), target_path))
            else:
                with tqdm(total=file_size, desc="Uploaded") as pbar:
                    upload_session_start_result = dbx.files_upload_session_start(
                        f.read(chunk_size)
                    )
                    pbar.update(chunk_size)
                    cursor = dropbox.files.UploadSessionCursor(
                        session_id=upload_session_start_result.session_id,
                        offset=f.tell(),
                    )
                    commit = dropbox.files.CommitInfo(path=target_path)
                    while f.tell() < file_size:
                        if (file_size - f.tell()) <= chunk_size:
                            metadata = dbx.files_upload_session_finish(
                                f.read(chunk_size), cursor, commit
                            )
                            print(
                                metadata
                            )
                        else:
                            dbx.files_upload_session_append(
                                f.read(chunk_size),
                                cursor.session_id,
                                cursor.offset,
                            )
                            cursor.offset = f.tell()
                            metadata = True
                        pbar.update(chunk_size)
        return metadata

    # DropBox Upload
    def dropbox_upload(self, path, file, file_name, x_days_ago, database_name):
        """
        Function Performs the Dropbox Upload.
        Upload sessions allow you to upload a single file in one or more requests, for example where the size of the
        file is greater than 150 MB. This call starts a new upload session with the given data. You can then use
        upload_session/append:2 to add more data and upload_session/finish to save all the data to a file in Dropbox.
        A single request should not upload more than 150 MB. The maximum size of a file one can upload to an upload
        session is 350 GB.
        An upload session can be used for a maximum of 48 hours. Attempting to use an
        UploadSessionStartResult.session_id with upload_session/append:2 or upload_session/finish more than 48 hours
        after its creation will return a UploadSessionLookupError.not_found.
        Calls to this endpoint will count as data transport calls for any Dropbox Business teams with a limit on the
        number of data transport calls allowed per month. For more information, see the Data transport limit page.
        :param path: Eg: /home/Apps/Backup_Odoo-125225052552/Backups from dropbox
        :param file: Tempdir/TempBackupfile
        :param x_days_ago: x days to remove,time span to remove files
        :param database_name: DB Name
        :return:
        """
        token = self.dropbox_token
        # Before Dump, we need to remove old backups.
        fetched_files = self.fetch_files(token, path, x_days_ago, database_name)  # fetching list of files to remove
        self.remove_batch(token, fetched_files)
        # Start Upload Session, since file can be > 150mb, Dropbox rule is to upload through
        # a session where files > 150mb
        upload_status = self.session_upload(token, file, path, file_name)
        return upload_status

    # create a filestore zip in temp dir and upload
    def dropbox_upload_filestore(self, db, filestore_path, dirr, x_days):
        """
        Here find files from filestore recursively and zip it.
        :param db: Current DB
        :param filestore_path: Filestore path
        :param dirr: backup path
        :param x_days: older than x days to remove files
        :return:
        """
        x_days_ago = self.calc_x_days(x_days)
        thetime = str(strftime("%Y-%m-%d-%H-%M-%S"))
        dump_dir = tempfile.mkdtemp()  # Temp Directory
        name = os.path.join(dump_dir, 'filestore' + '_' + thetime)
        filestore_path = os.path.join(filestore_path, db)
        filestore = filestore_path if os.path.exists(filestore_path) else odoo.tools.config.filestore(db)

        # Make sure the filestore path is acessible.
        self._check_path_access(filestore)

        self.log("Filestore Backup Started...............")

        # Backup Filestore
        try:
            if os.path.exists(filestore):  # If Path Exists?
                # os.makedirs(name, mode=0o777, exist_ok=True)  # Create a new path for backup
                os.path.exists(name)
                zipfile = shutil._make_zipfile(base_name=name, base_dir=filestore)  # Zip Recursively filestore
                status = self.dropbox_upload(path=dirr, file=zipfile, file_name=zipfile.split('/')[-1],
                                             x_days_ago=x_days_ago,
                                             database_name='filestore')
                if status in ['Invalid URL', 'Invalid File']:
                    self.log("Invalid File / URL", "Exception")
                    self.message_post(
                        body="Filestore Failed. Info: %s" % status,
                        subtype_xmlid="mail.mt_comment",
                        message_type="comment")
                elif status:
                    self.log("%s Filestore dump finished" % name)
                    self.log("MetaData: \n %s" % status)
                    self.log("Backup job complete.")
                    self.message_post(
                        body="Backup Completed. \n MetaData: \n %s" % status,
                        subtype_xmlid="mail.mt_comment",
                        message_type="comment")
                else:
                    raise IOError
                self.log("Filestore Backup Done ..............%s" % zipfile)
                self.message_post(
                    body="FileStore Backup Success.\n Path: " + 'filestore' + '_' + thetime,
                    subtype_xmlid="mail.mt_comment",
                    message_type="comment")
        except Exception as e:
            self.log("Filestore Backup Failed......... %s" % ("File exists" + '/filestore/'), type='exception')
            self.message_post(
                body="File exists. Info: %s" % (str(e) or repr(e)),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
            return False
        finally:
            shutil.rmtree(dump_dir)  # Remove the temp dir
        self.log("Filestore Backup Done...............")

    # Dump DB
    def dropbox_dump_start(self, db, user, password, host, dirr, dumper, x_days):
        """
        Function DUMP Database from postgres db pool to DropBox.
        :param db: Current Database to DUMP
        :param user: Database USER from odoo-server-config
        :param password: Password USER from odoo-server-config
        :param host: host in default localhost, will get host from odoo-server-config
        :param dirr: Eg: /home/Apps/Backup_Odoo-125225052552/Backups
        :param dumper: PSQL Query to DUMP according to the format c,t,p
        :param x_days: Interval to remove old backups.
        :return: False if error.
        """
        USER = user.strip()
        PASS = password.strip()
        HOST = host.strip()
        dumper = dumper
        x_days = x_days or 1
        database_list = []

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
                if dump_dir:
                    dirpath = os.path.join(dump_dir, file_name.strip())
                    if dumper != 'with filestore':
                        command = dumper.format(db_name=database_name.strip(), b_db_name=dirpath,
                                                user=USER, host=HOST.strip())
                        self.log(command)
                        subprocess.call(command, shell=True)
                    else:
                        filepath = os.path.join(dump_dir, file_name.strip())
                        with open(filepath, "wb") as f:
                            odoo.service.db.dump_db(database_name.strip(), f)
                    # Here We Perform DropBox Upload
                    glob_list = glob.glob(os.path.join(dump_dir, file_name) + '*')
                    for file in glob_list:
                        status = self.dropbox_upload(path=dirr, file=file, file_name=file.split('/')[-1],
                                                     x_days_ago=x_days_ago,
                                                     database_name=database_name.strip())
                        if status in ['Invalid URL', 'Invalid File']:
                            self.log("Invalid File / URL", "Exception")
                            self.message_post(
                                body="Filestore Failed. Info: %s" % status,
                                subtype_xmlid="mail.mt_comment",
                                message_type="comment")
                        elif status:
                            self.log("%s Backup dump finished" % file)
                            self.log("MetaData: \n %s" % status)
                            self.log("Backup job complete.")
                            self.message_post(
                                body="Backup Completed. \n MetaData: \n %s" % status,
                                subtype_xmlid="mail.mt_comment",
                                message_type="comment")
                        else:
                            raise IOError
                        self.log("Backup Done ..............%s" % file)
                shutil.rmtree(dump_dir)
        except Exception as e:
            self.log(e, "Exception")
            self.message_post(
                body="Backup Error.\n Info: %s" % (str(e) or repr(e)),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
