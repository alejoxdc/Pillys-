# -*- coding: utf-8 -*-
import subprocess
import os
import glob
import time
import logging
import shutil
import odoo
import tempfile
import requests
import json
import datetime
import simplejson

from time import strftime
from odoo import models, fields, api

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

_logger = logging.getLogger("############### Backup ODOO DB -> Google Drive Logs #################")


class OdooBackupDrive(models.Model):
    """
    Base CLass for Backup DB To Google Drive
    """
    _inherit = 'auto.backup'

    drive_client_id = fields.Char("Google Drive Client ID", copy=False)
    drive_secret_id = fields.Char("Google Drive Secret ID", copy=False)
    drive_uri = fields.Char(string='Tocken URI',
                            copy=False,
                            compute='_get_drive_authentication_url')
    drive_auth_code = fields.Char("Google Drive Auth Code", copy=False)
    drive_refresh_token = fields.Char("Google Drive Access Token", copy=False)

    def _get_drive_authentication_url(self):
        """
        Here we fetch the auth URL to grant access
        """
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')

        # Replace these with your own client ID, secret, and redirect URI
        CLIENT_ID = self.drive_client_id
        REDIRECT_URI = base_url + "/drive/authentication"
        # The scope of the API you want to access
        SCOPE = "https://www.googleapis.com/auth/drive"

        # Set the authorization code URL and the token URL
        auth_url = "https://accounts.google.com/o/oauth2/auth"

        # Set the authorization code request parameters
        auth_params = {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE,
            "response_type": "code",
        }

        # Generate the authorization URL
        auth_url = auth_url + "?" + urlencode(auth_params)

        # Print the authorization URL and prompt the user to visit it
        self.drive_uri = auth_url

    def _get_drive_access_tocken(self):
        """
        We fetch access token along with the refresh token to get new access token when expires
        """
        drive_backups = self
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')

        # Replace these with your own client ID, secret, and redirect URI
        CLIENT_ID = drive_backups.drive_client_id
        CLIENT_SECRET = drive_backups.drive_secret_id
        AUTH_CODE = drive_backups.drive_auth_code
        REDIRECT_URI = base_url + "/drive/authentication"

        # Set the token URL and request data
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'code': AUTH_CODE,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'redirect_uri': REDIRECT_URI,
            'grant_type': 'authorization_code'
        }

        # Make the token request
        response = requests.post(token_url, data=token_data)
        # Check for success
        if response.status_code == 200:
            # Get the access token
            token = response.json()['access_token']
            refresh_token = response.json()['refresh_token']
            self.drive_refresh_token = refresh_token
            return token
        else:
            """
            We need to request for a resresh token.
            """
            refresh_token = self.drive_refresh_token

            # Set the token URL and request data
            token_url = 'https://oauth2.googleapis.com/token'
            token_data = {
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }

            # Make the token request
            response = requests.post(token_url, data=token_data)

            # Check for success
            if response.status_code == 200:
                # Get the new access token
                token = response.json()['access_token']
                return token
            else:
                print(f'Request failed with status code {response.status_code}')
                self.log(f'Request failed with status code {response.status_code}')
                self.message_post(
                    body=f"Access token request failed. Info: File {response.status_code}",
                    subtype_xmlid="mail.mt_comment",
                    message_type="comment")

    @api.model
    def set_drive_auth_code(self, code):
        """

        :param code:
        :return:
        """
        drive_backups = self.env['auto.backup'].search([('backup_mode', '=', 'drive')], limit=1)
        drive_backups.write({'drive_auth_code': code})
        action = self.env.ref('auto_backup_odoo.action_auto_backup_odoo_config')
        menu = self.env.ref('auto_backup_odoo.menu_auto_backup_db_psql_config')
        return '/web#id=%s&action=%s&model=auto.backup&view_type=form&cids=&menu_id=%s' % (
            drive_backups[0].id, action.id, menu.id)

    def resumable_upload(self, range='*', uri='', file_size=''):
        """
        A 308 Resume Incomplete response indicates that you need to continue to upload the file.
         If you received a 308 Resume Incomplete response, process the response's Range header,
          to determine which bytes the server has received. If the response doesn't have a Range header,
           no bytes have been received. For example, a Range header of bytes=0-42
            indicates that the first 43 bytes of the file have been received and that the
            next chunk to upload would start with byte 43.
        :param range:
        :param uri:
        :param file_size:
        :return:
        """
        if range == '*':
            headers = {
                "Content-Range": "%s/%s" % (range, file_size)
            }
        else:
            range = int(range) + 1
            file_sizee = int(file_size) - 1
            headers = {"Content-Range": "bytes %s-%s/%s" % (range, file_sizee - 1, file_size)}
        upload_status = requests.request(
            "PUT", uri, headers=headers)

        if upload_status.status_code in [200, 201]:
            return upload_status.status_code
        elif upload_status.status_code == 308:
            try:
                range = upload_status.headers['Range']
                range = str(range).split('-')[1]
            except Exception:
                range = '*'
            self.resumable_upload(range, uri, file_size)
        elif upload_status.status_code == 404:
            return False
        else:
            return False

    def upload_file(self, path, file, x_days_ago, database_name):
        """
        Function Performs the Google Drive Upload.
        :param path: Eg: https://drive.google.com/drive/u/0/folders/1vzEwZyIBBthjvgKK97OYiByWAI1u6k4
        :param file: Tempdir/TempBackupfile
        :param x_days_ago: x days to remove,time span to remove files
        :param database_name: DB Name
        :return:
        """
        key = self._get_key_from_url(path)
        file_exists = os.path.isfile(file)
        ACCESS_TOCKEN = self._get_drive_access_tocken()
        UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
        GET_URL = "https://www.googleapis.com/drive/v3/files"
        if not key:
            return "Invalid URL"
        if not file_exists:
            return "Invalid File"

        file_info = os.stat(file)

        # We Need to remove old backup files from drive before upload.
        # use GET With Search Params, Then use DELETE
        headers = {
            'Authorization': "Bearer %s" % ACCESS_TOCKEN,
            'Accept': "application / json"
        }
        querystring = {
            "fields": "files(id,name,mimeType,createdTime)",
            "q": "'%s' in parents and name contains '%s'" % (key, database_name)}
        contents = requests.request(
            "GET", GET_URL, data={}, headers=headers, params=querystring)
        if contents.status_code == 200:
            for data in simplejson.loads(contents._content)['files']:
                file_mtime = datetime.datetime.strptime(data['createdTime'], "%Y-%m-%dT%H:%M:%S.%fZ").timetuple()
                file_mtime = time.mktime(file_mtime)
                if file_mtime < x_days_ago:
                    delete_response = requests.request(
                        "DELETE", GET_URL + '/%s' % data['id'], data={}, headers=headers, )
                    if delete_response.status_code in [204, 200]:
                        self.log("Drive File Unlink Success. Info: File %s" % data['name'])
                        self.message_post(
                            body="Unlink Success. Info: File %s" % data['name'],
                            subtype_xmlid="mail.mt_comment",
                            message_type="comment")
                    else:
                        self.log("Drive File Unlink Failed. Info: File %s" % data['name'])
                        self.message_post(
                            body="Unlink Failed. Info: File %s" % data['name'],
                            subtype_xmlid="mail.mt_comment",
                            message_type="comment")
                else:
                    self.log("Keeping FIle. Info: File %s" % data['name'])
        else:
            self.log("File Access Error!", "Exception")

        headers = {
            'Authorization': "Bearer %s" % ACCESS_TOCKEN,
            'Content-Type': "application/json; charset=UTF-8",
            'Content-Length': str(file_info.st_size),
            'X-Upload-Content-Type': "application/zip",
            'X-Upload-Content-Length': str(file_info.st_size)
        }
        querystring = {"uploadType": "resumable"}
        payload = {
            "name": "%s" % file.split('/') and file.split('/')[-1] or file,
            "parents": ["%s" % key]
        }
        response = requests.request(
            "POST", UPLOAD_URL, data=json.dumps(payload), headers=headers, params=querystring)

        if response.status_code == 200:
            uri = response.headers['Location']
            headers = {
                'Content-Length': str(file_info.st_size),
            }
            resumable_response = requests.request(
                "PUT", uri, data=open("%s" % file, "rb"), headers=headers)
            if resumable_response.status_code == 200:
                self.log('File Successfully Uploaded To Google Drive.')
                self.message_post(
                    body="Backup Successfully Uploaded To Google Drive.",
                    subtype_xmlid="mail.mt_comment",
                    message_type="comment")
                return True
            elif resumable_response.status_code in [503, 500]:
                """
                If an upload request is terminated before a response,
                or if you receive a 503 Service Unavailable response,
                then you need to resume the interrupted upload.
                To request the upload status, create an empty PUT request to the resumable session URI.
                """
                upload_status = self.resumable_upload(uri=uri, file_size=str(file_info.st_size))
                if upload_status in [200, 201]:
                    self.log('File Successfully Uploaded To Google Drive.')
                    self.message_post(
                        body="Backup Successfully Uploaded To Google Drive.",
                        subtype_xmlid="mail.mt_comment",
                        message_type="comment")
                elif upload_status == 400:
                    self.log("Google Drive Upload Error!")
                    self.message_post(
                        body="Google Drive Upload Error!",
                        subtype_xmlid="mail.mt_comment",
                        message_type="comment")
        elif response.status_code in [400, 304]:
            return False

    def drive_upload_filestore(self, db, filestore_path, dirr, x_days):
        """
        Find files from the filestore path and zip it recursively
        :param db: Current DB
        :param filestore_path: Filestore path
        :param dirr: drive backup path
        :param x_days: older than x days to remove files
        :return:
        """
        x_days_ago = self.calc_x_days(x_days)
        thetime = str(strftime("%Y-%m-%d-%H-%M-%S"))
        dump_dir = tempfile.mkdtemp()
        name = os.path.join(dump_dir, 'filestore' + '_' + thetime)
        filestore_path = os.path.join(filestore_path, db)
        filestore = filestore_path if os.path.exists(filestore_path) else odoo.tools.config.filestore(db)
        self._check_path_access(filestore)

        self.log("Filestore Backup Started...............")

        # Backup Filestore
        try:
            if os.path.exists(filestore):  # If Path Exists?
                zipfile = shutil._make_zipfile(base_name=name, base_dir=filestore)  # Zip Recursively filestore
                status = self.upload_file(path=dirr, file=zipfile, x_days_ago=x_days_ago,
                                          database_name='filestore')
                if status in ['Invalid URL', 'Invalid File']:
                    self.log("Invalid File / URL", "Exception")
                    self.message_post(
                        body="Filestore Failed. Info: %s" % status,
                        subtype_xmlid="mail.mt_comment",
                        message_type="comment")
                elif status:
                    self.log("%s Filestore dump finished" % name)
                    self.log("Backup job complete.")
                    self.message_post(
                        body="Backup Completed.",
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
    def drive_dump_start(self, db, user, password, host, dirr, dumper, x_days):
        """
        Function DUMP Database from postgres db pool to Google Drive.
        :param db: Current Database to DUMP
        :param user: Database USER from odoo-server-config
        :param password: Password USER from odoo-server-config
        :param host: host in default localhost, will get host from odoo-server-config
        :param dirr: Eg: https://drive.google.com/drive/u/0/folders/1vzEwZyIBBthjvgKK97OYiByWAI1u6k4
        :param dumper: PSQL Query to DUMP according to the format c,t,p
        :param x_days: Interval to remove old backups.
        :return: False if error.
        """
        USER = user.strip()
        PASS = password.strip()
        HOST = host.strip()
        # BACKUP_DIR = dirr.strip() if dirr.strip()[-1] == '/' else dirr.strip() + '/'
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
                    # Here We Perform Google Drive Upload
                    glob_list = glob.glob(os.path.join(dump_dir, file_name) + '*')
                    for file in glob_list:
                        status = self.upload_file(path=dirr, file=file, x_days_ago=x_days_ago,
                                                  database_name=database_name.strip())
                        if status in ['Invalid URL', 'Invalid File']:
                            self.log("Invalid File / URL", "Exception")
                            self.message_post(
                                body="Failed. Info: %s" % status,
                                subtype_xmlid="mail.mt_comment",
                                message_type="comment")
                        elif status:
                            self.log("%s dump finished" % database_name)
                            self.log("Backup job complete.")
                            self.message_post(
                                body="Backup Completed.",
                                subtype_xmlid="mail.mt_comment",
                                message_type="comment")
                        else:
                            raise IOError
                shutil.rmtree(dump_dir)
        except Exception as e:
            self.log(e, "Exception")
            self.message_post(
                body="Backup Error.\n Info: %s" % (str(e) or repr(e)),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
