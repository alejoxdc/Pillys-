# -*- coding: utf-8 -*-
import glob
import logging
import os
import shutil
import subprocess
import tempfile
from time import strftime
import time
from odoo import models, fields

import odoo
import boto3
from botocore.exceptions import ClientError

_logger = logging.getLogger("############### Backup ODOO DB -> S3 Logs #################")


class OdooBackupAWS(models.Model):
    """
    Base CLass for Backup DB To AWS
    """
    _inherit = 'auto.backup'

    # S3 Fields
    aws_access_key_id = fields.Char(string='AWS Access Key',
                                    copy=False)
    aws_secret_key_id = fields.Char(string='AWS Secret Key',
                                    copy=False)
    bucket_name = fields.Char(string='Bucket Name',
                              copy=False)

    # Remove the fetched files
    def remove_batch_aws(self, s3_client, bucket, fetched_files):
        """
        Remove files as a batch
        :param s3_client: S3 Client
        :param bucket: S3 Bucket Name
        :param fetched_files: list of file keys to remove
        :return: True if success else Nothing Since it's optional
        """
        is_deleted = False
        if fetched_files:
            is_deleted = s3_client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": fetched_files},
            )
        # We don't need to check the asynchronous status.
        if is_deleted['ResponseMetadata']['HTTPStatusCode'] == 200:
            self.log("Dropbox File Unlink Success %s" % fetched_files)
            self.message_post(
                body="Unlink Success. Info: File %s" % is_deleted['deleted'],
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
        else:
            self.log("Dropbox File Unlink Failed %s")
            self.message_post(
                body="Unlink Failed",
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
        return True

    # Fetch files from the specified path
    def fetch_files_aws(self, s3_client, bucket, path, x_days, database_name):
        """
        fetch files in a dir to compare and remove from path, according to the x days to remove.
        param s3_client: S3 client object
        :param bucket: S3 Bucket Name
        :param path: Path in s3 -> Bucket name + directory or ''
        :param x_days: timetuple to compare with s2 last modified date
        :param database_name: DB Name
        :return: [] list of file keys
        """
        prefix = path
        fetched_objects = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix,
            Delimiter="/",
        )

        if 'Contents' not in fetched_objects:
            return []

        file_list = []
        file_list.extend([{"Key": key['Key']} for key in fetched_objects['Contents']
                          if time.mktime(key['LastModified'].timetuple()) < x_days and key[
                              'Key'] in database_name and not (path == key['Key'])
                          ])
        while fetched_objects['IsTruncated']:
            continuation_key = fetched_objects['NextContinuationToken']
            fetched_objects = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter="/",
                                                        ContinuationToken=continuation_key)
            file_list.extend([{"Key": key['Key']} for key in fetched_objects['Contents']
                              if time.mktime(key['LastModified'].timetuple()) < x_days and key[
                                  'Key'] in database_name and not (path == key['Key'])
                              ])
        return file_list

    # Upload data in a session.
    def upload_s3(self, s3_client, bucket, file, file_name, path):
        """
        Upload file as object to an S3 bucket.
        :param s3_client: S3 client object
        :param bucket: S3 Bucket Name
        :param path: Path in s3 -> Bucket name + directory or ''
        :param file: File to upload
        :param file_name: S3 object name. If not specified then file_name is used
        :return: True if file was uploaded, else False
        """
        # If S3 object_name was not specified, use file_name
        file_name = os.path.join(path, file_name)
        # Upload the file
        try:
            with open(file, "rb") as f:
                s3_client.upload_fileobj(f, bucket, file_name)
        except ClientError as e:
            logging.error(e)
            return False
        return True

    # DropBox Upload
    def aws_upload(self, path, file, file_name, x_days_ago, database_name):
        """
        Function Performs the s3 Upload.
        :param path: Eg: folderName/
        :param file: Tempdir/TempBackupfile
        :param x_days_ago: x days to remove,time span to remove files
        :param database_name: DB Name
        :param file_name: filename in s3
        :return:
        """
        access_key = self.aws_access_key_id
        secret_key = self.aws_secret_key_id
        bucket = self.bucket_name

        s3_client = boto3.client('s3',
                                 aws_access_key_id=access_key,
                                 aws_secret_access_key=secret_key)
        # Before Dump, we need to remove old backups.
        fetched_files = self.fetch_files_aws(s3_client, bucket,
                                             path, x_days_ago, database_name)  # fetching list of files to remove
        if fetched_files:
            self.remove_batch_aws(s3_client, bucket, fetched_files)
        upload_status = self.upload_s3(s3_client, bucket, file, file_name, path)
        return upload_status

    # create a filestore zip in temp dir and upload
    def aws_upload_filestore(self, db, filestore_path, dirr, x_days):
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
                status = self.aws_upload(path=dirr, file=zipfile, file_name=zipfile.split('/')[-1],
                                         x_days_ago=x_days_ago,
                                         database_name='filestore')
                if status:
                    self.log("%s Filestore dump finished" % name)
                    self.log("MetaData: \n %s" % status)
                    self.log("Backup job complete.")
                    self.message_post(
                        body="Filestore Backup Completed. %s" % status,
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
    def aws_dump_start(self, db, user, password, host, dirr, dumper, x_days):
        """
        Function DUMP Database from postgres db pool to s3.
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
                    # Here We Perform s3 Upload
                    glob_list = glob.glob(os.path.join(dump_dir, file_name) + '*')
                    for file in glob_list:
                        status = self.aws_upload(path=dirr, file=file, file_name=file.split('/')[-1],
                                                 x_days_ago=x_days_ago,
                                                 database_name=database_name.strip())
                        if status:
                            self.log("%s Backup dump finished" % file)
                            self.log("Backup job complete.")
                            self.message_post(
                                body="Backup Completed. Status %s" % status,
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
