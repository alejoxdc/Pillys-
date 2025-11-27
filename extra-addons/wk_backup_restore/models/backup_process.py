# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################

from odoo import fields, api, models, tools
from odoo.exceptions import UserError
from odoo.tools.config import config

from odoo.addons.wk_backup_restore.models.lib import manage_backup_crons
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os

import logging

_logger = logging.getLogger(__name__)


LOCATION = [
    ('local', 'Local'),
    ('remote', 'Remote Server'),
]

CYCLE = [
    ('half_day', 'Twice a day'),
    ('daily', 'Daily'),
    ('weekly', 'Weekly'),
    ('monthly', 'Monthly'),
    ('yearly', 'Yearly'),
]

STATE = [
    ('draft', 'Draft'),
    ('confirm', 'Confirm'),
    ('running', 'Running'),
    ('cancel', 'Cancel')
]

class BackupProcess(models.Model):
    _name = "backup.process"
    _description="Backup Process"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id desc"

    def _default_db_name(self):
        return self._cr.dbname

    name = fields.Char(string="Process Name", default='New', help="Display name for the backup process.")
    frequency = fields.Integer(string="Frequency", default=1, help="Frequency for backuping the database.")
    frequency_cycle = fields.Selection(selection=CYCLE, string="Frequency Cycle", help="Select frequency cycle of Database Backup.", tracking=True)
    storage_path = fields.Char(string="Storage Path", required=True, help="The directory path where the backup files will be stored on the server. Please enter your preferred backup directory path.", tracking=True)
    backup_location = fields.Selection(selection=LOCATION, string="Backup Location", default="local", help="Server where the backup file will be stored.")
    retention = fields.Integer(string="Backup Retention Count", default=7, help="Count of recent backups that will be retained after dropping old backups on server.")
    # start_time = fields.Datetime(string="Backup Starting Time", help="Time from when the database backup can be started.")
    db_name = fields.Char(string="Database Name", default=_default_db_name, help="Database used for the creating the backup.", tracking=True)
    backup_starting_time = fields.Datetime(string="Backup Starting Time", help="Set Database Backup start date and time.")
    state = fields.Selection(selection=STATE, default='draft', help="Current state of the backup process.")
    update_requested = fields.Boolean(string="Update Requested", default=False, help="Checked if any backup is requested in the database backup.")
    # master_pass = fields.Char(string="Master Password")
    backup_details_ids = fields.One2many(comodel_name="backup.process.detail", inverse_name="backup_process_id", string="Backup Details", help="Details of the database backups that has been created.")
    backup_format = fields.Selection([('zip', 'zip (includes filestore)'), ('dump', 'pg_dump custom format (without filestore)')], string="Backup Format", default="zip", help="Select the file format of the data backup file.", tracking=True) 
    enable_retention = fields.Boolean(string="Drop Old Backups", default=False, help="Check if you want to drop old backups stored on the server.")
    remote_server_id = fields.Many2one(comodel_name="backup.remote.server", string="Backup Remote Server", domain=[('state', '=', 'validated')])
    backup_file = fields.Binary(string="Backup File", help="Temporary storage for backup file download")
    

    @api.onchange('frequency_cycle')
    def change_frequency_value(self):
        """
            Method to change the value of frequency for Twice a day
        """

        if self.frequency_cycle == 'half_day':
            self.frequency = 2
        else:
            self.frequency = 1
            
    @api.onchange('backup_location')
    def change_backup_location(self):
        """
            Method to check the validated remote servers
        """
        if self.backup_location == 'remote':
            backup_servers = self.env['backup.remote.server'].sudo().search([('state', '=', 'validated')])
            if not backup_servers:
                raise UserError("No validated remote servers found. Please configure a remote server first!!")
        self.remote_server_id = None            
            
            
    @api.constrains('retention')
    def check_retention_value(self):
        """
            Method to check the value of retention field
        """

        if self.enable_retention:
            if self.retention < 1:
                raise UserError("Backup Retention Count should be at least 1.")

    def call_backup_script(self, master_pass=None, port_number=None, url=None, db_user=None, db_password=None, kwargs={}):
        """
            Called by create_backup_request method, defined below
            Method to call script to create a cron for manage backups,
            calling script require few arguments, some are passed in this method same are prepared below
        """
        try:
            db_user = db_user or config.get('db_user')
            db_password = db_password or config.get('db_password')
            module_path = tools.misc.file_path('wk_backup_restore')
            module_path = module_path + '/models/lib/saas_client_backup.py'
            backup_format = self.backup_format or "zip"
            backup_location = self.backup_location
            res = None
            if hasattr(self,'_call_%s_backup_script'%backup_location):## if you want to update dictionary then you can define this function _call_{backup_location}_backup_script
                res = getattr(self,'_call_%s_backup_script'%backup_location)(master_pass,port_number,url,db_user,db_password,backup_format, kwargs)
            return res
        except Exception as e:
            body = "Cannot create backup cron!! ERROR: {}".format(e)
            self.message_post(body=body, subject="Backup Creation Exception")
            _logger.error(f"------Error While Creating Backup Request----{e}--------------")
            
        
    
    def _call_local_backup_script(self, master_pass=None, port_number=None, url=None, db_user=None, db_password=None, backup_format="zip", kwargs={}):
        """
            Called by call_backup_script method, defined above
            Method to call script to create a cron for manage backups,
            calling script require few arguments, some are passed in this method same are prepared below
        """
        res = None
        if self.backup_location == "local":
            module_path = tools.misc.file_path('wk_backup_restore')
            module_path = module_path + '/models/lib/saas_client_backup.py'
            res = manage_backup_crons.add_cron(master_pass=master_pass, main_db=self._cr.dbname, db_name=self.db_name, backup_location=self.backup_location, frequency=self.frequency, frequency_cycle=self.frequency_cycle, storage_path=self.storage_path, url=url, db_user=db_user, db_password=db_password, process_id=self.id, module_path=module_path, backup_format=backup_format, backup_starting_time=self.backup_starting_time, kwargs=kwargs)
        
        if res.get('success'):
            self.state = 'running'
        else:
            body = "Cannot create backup cron. Error: {}".format(res.get('msg'))
            self.message_post(body=body, subject="Backup Creation Exception")
        return res
    
    
    def _call_remote_backup_script(self, master_pass=None, port_number=None, url=None, db_user=None, db_password=None, backup_format="zip", kwargs=dict()):
        """
            Called by call_backup_script method, defined above
            Method to call script to create a cron for manage remote database backups,
            calling script require few arguments, some are passed in this method same are prepared below
        """
        res = None
        if self.backup_location == "remote":
            module_path = tools.misc.file_path('wk_backup_restore')
            module_path = module_path + '/models/lib/saas_client_backup.py'
            kwargs.update(
                rhost = self.remote_server_id.sftp_host,
                rport = self.remote_server_id.sftp_port,
                ruser = self.remote_server_id.sftp_user,
                rpass = self.remote_server_id.sftp_password,
                temp_bkp_path = self.remote_server_id.temp_backup_dir,
            )
            res = manage_backup_crons.add_cron(master_pass=master_pass, main_db=self._cr.dbname, db_name=self.db_name, backup_location=self.backup_location, frequency=self.frequency, frequency_cycle=self.frequency_cycle, storage_path=self.storage_path, url=url, db_user=db_user, db_password=db_password, process_id=self.id, module_path=module_path, backup_format=backup_format,backup_starting_time=self.backup_starting_time, kwargs=kwargs)
        
        if res.get('success'):
            self.state = 'running'
        else:
            body = "Cannot create backup cron. Error: {}".format(res.get('msg'))
            self.message_post(body=body, subject="Backup Creation Exception")
        return res
    

    def update_backup_request(self):
        """
            Method called from Cron, 
            Method called the script to update already created cron.
        """

        res = manage_backup_crons.update_cron(db_name=self.db_name, process_id=str(self.id), frequency=self.frequency, frequency_cycle=self.frequency_cycle)
        if res.get('success'):
            self.update_requested = False
    
    def create_backup_request(self):
        """
            Create Odoo internal cron job for backup scheduling
        """
        master_pass = config.get('master_passwd')
        if not master_pass:
            body = "Cannot create backup cron: Master Password(master_passwd) is not set in conf file"
            self.message_post(body=body, subject="Backup Creation Exception")
            _logger.error("------Error While Creating Backup Request--Master Password(master_passwd) is not set in conf file!!----------------")
            return

        # Create Odoo internal cron job instead of system cron
        self._create_odoo_cron_job()
        self.state = 'running'

    def _create_odoo_cron_job(self):
        """
        Create an internal Odoo cron job for this backup process - Executes every 8 hours
        """
        # Remove existing cron if any
        existing_cron = self.env['ir.cron'].search([
            ('name', '=', f'Backup Process {self.id}'),
            ('active', '=', True)
        ])
        if existing_cron:
            existing_cron.unlink()
        
        # Simple configuration: Execute backup every 8 hours
        from datetime import datetime, timedelta
        
        # Start the cron in 8 hours from now (or use backup_starting_time if it's in the future)
        now = datetime.now()
        next_execution = self.backup_starting_time if self.backup_starting_time > now else now + timedelta(hours=8)
        
        # Create new cron job - every 8 hours
        cron_vals = {
            'name': f'Backup Process {self.id} - Every 8 Hours',
            'model_id': self.env.ref('wk_backup_restore.model_backup_process').id,
            'state': 'code',
            'code': f'env["backup.process"].browse({self.id}).execute_scheduled_backup()',
            'interval_number': 8,
            'interval_type': 'hours',
            'nextcall': next_execution,
            'active': True,
        }
        
        self.env['ir.cron'].create(cron_vals)
        _logger.info(f"Created Odoo cron job for backup process {self.id} - Every 8 hours starting at {next_execution}")

    def execute_scheduled_backup(self):
        """
        Method called by Odoo cron to execute backup every 8 hours
        """
        if self.state == 'running':
            try:
                from datetime import datetime
                _logger.info(f"Starting scheduled backup for process {self.id} at {datetime.now()}")
                
                # Execute the backup using our existing method
                self.download_backup_now()
                
                # Log success
                _logger.info(f"✓ Scheduled backup completed successfully for process {self.id} - Next backup in 8 hours")
                self.message_post(
                    body=f"Automatic backup completed successfully at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                    subject="Scheduled Backup Success"
                )
            except Exception as e:
                _logger.error(f"✗ Scheduled backup failed for process {self.id}: {str(e)}")
                self.message_post(
                    body=f"Scheduled backup failed: {str(e)}", 
                    subject="Scheduled Backup Error"
                )
        else:
            _logger.warning(f"Backup process {self.id} is not in 'running' state. Current state: {self.state}")

    def remove_attached_cron(self):
        """
            Called by the button over backup process page,
            To cancel the Backup Process record and remove associated cron job
        """
        if self.state == 'running':
            # Remove Odoo internal cron job
            existing_cron = self.env['ir.cron'].search([
                ('name', '=', f'Backup Process {self.id}'),
                ('active', '=', True)
            ])
            if existing_cron:
                existing_cron.unlink()
                _logger.info(f"Removed Odoo cron job for backup process {self.id}")
        
        self.state = 'cancel'
        return {'success': True}
    
    def download_backup_now(self):
        """
        Execute backup immediately and save to user's specified folder
        """
        if not self.storage_path:
            raise UserError("Please specify a Storage Path before downloading backup.")
        
        try:
            # Create the directory if it doesn't exist
            import os
            os.makedirs(self.storage_path, exist_ok=True)
            
            # Execute backup immediately using the same script
            from odoo.addons.wk_backup_restore.models.lib import saas_client_backup
            
            # Create backup instance
            backup_obj = saas_client_backup.BackupStorage()
            
            # Prepare arguments similar to cron execution
            class Args:
                pass
            
            args = Args()
            args.mpswd = config.get('master_passwd') or 'admin_password'
            args.url = f"localhost:{config.get('http_port', '8069')}"
            args.dbname = self.db_name
            args.maindb = self.env.cr.dbname
            args.dbuser = config.get('db_user')
            args.dbpassword = config.get('db_password')
            args.processid = self.id
            args.bkploc = 'local'
            args.path = self.storage_path
            args.backup_format = self.backup_format or 'zip'
            args.is_remote_client = False
            args.temp_bkp_path = None
            args.remote_server_id = None
            
            # Execute backup
            result = backup_obj.manage_backup_files(args)
            
            if result.get('status'):
                message = f"Backup downloaded successfully to: {self.storage_path}"
                self.message_post(body=message, subject="Manual Backup Success")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Backup Success!',
                        'message': message,
                        'type': 'success',
                    }
                }
            else:
                error_msg = result.get('message', 'Unknown error occurred')
                raise UserError(f"Backup failed: {error_msg}")
                
        except Exception as e:
            error_message = f"Failed to create backup: {str(e)}"
            self.message_post(body=error_message, subject="Manual Backup Error")
            raise UserError(error_message)
    
    def save_backup_to_server(self):
        """
        Execute backup immediately and save directly to server folder (no download)
        """
        if not self.storage_path:
            raise UserError("Please specify a Storage Path before saving backup to server.")
        
        try:
            import os
            import subprocess
            import tempfile
            from datetime import datetime
            
            # Use /home/odoo-backups which should work better
            backup_dir = '/home/odoo-backups'
            try:
                os.makedirs(backup_dir, mode=0o755, exist_ok=True)
                _logger.info(f"✅ Using backup directory: {backup_dir}")
            except Exception as e:
                # Fallback to a temp directory in /tmp that persists longer
                backup_dir = '/tmp/odoo-backups-permanent'
                os.makedirs(backup_dir, mode=0o777, exist_ok=True)
                _logger.warning(f"Cannot create {backup_dir}, using fallback: {backup_dir}")
            
            # Generate backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{self.db_name}_backup_{timestamp}.zip"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            _logger.info(f"🔍 DEBUG - Original storage path: {self.storage_path}")
            _logger.info(f"🔍 DEBUG - Using backup directory: {backup_dir}")
            _logger.info(f"🔍 DEBUG - Backup filename: {backup_filename}")
            _logger.info(f"🔍 DEBUG - Full backup path: {backup_path}")
            _logger.info(f"🔍 DEBUG - Directory exists: {os.path.exists(backup_dir)}")
            _logger.info(f"🔍 DEBUG - Directory writable: {os.access(backup_dir, os.W_OK)}")
            
            # Create backup using pg_dump and zip
            with tempfile.TemporaryDirectory() as temp_dir:
                sql_file = os.path.join(temp_dir, f"{self.db_name}.sql")
                
                # Get database connection parameters
                db_host = config.get('db_host', 'localhost')
                db_port = config.get('db_port', '5432')
                db_user = config.get('db_user', 'odoo')
                db_password = config.get('db_password', '')
                
                # Create pg_dump command
                cmd = [
                    'pg_dump',
                    '-h', db_host,
                    '-p', str(db_port),
                    '-U', db_user,
                    '-f', sql_file,
                    '--no-password',
                    self.db_name
                ]
                
                # Set password environment variable if needed
                env = os.environ.copy()
                if db_password:
                    env['PGPASSWORD'] = db_password
                
                # Execute pg_dump
                _logger.info(f"🔄 Ejecutando pg_dump: {' '.join(cmd)}")
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                
                _logger.info(f"📊 pg_dump return code: {result.returncode}")
                if result.stdout:
                    _logger.info(f"📝 pg_dump stdout: {result.stdout}")
                if result.stderr:
                    _logger.error(f"⚠️ pg_dump stderr: {result.stderr}")
                
                if result.returncode == 0:
                    # Create zip file
                    _logger.info(f"📦 Creando archivo ZIP: {backup_path}")
                    import zipfile
                    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        _logger.info(f"➕ Agregando SQL file: {sql_file}")
                        zipf.write(sql_file, f"{self.db_name}.sql")
                        
                        # Add filestore if exists
                        filestore_path = config.get('data_dir', '/opt/odoo/data') + f'/filestore/{self.db_name}'
                        _logger.info(f"🗂️ Buscando filestore en: {filestore_path}")
                        if os.path.exists(filestore_path):
                            _logger.info(f"✅ Filestore encontrado, agregando archivos...")
                            file_count = 0
                            for root, dirs, files in os.walk(filestore_path):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    arcname = os.path.relpath(file_path, os.path.dirname(filestore_path))
                                    zipf.write(file_path, arcname)
                                    file_count += 1
                            _logger.info(f"📁 {file_count} archivos agregados del filestore")
                        else:
                            _logger.warning(f"⚠️ Filestore no encontrado en: {filestore_path}")
                    
                    _logger.info(f"✅ ZIP creado exitosamente: {backup_path}")
                    
                    # Verify file was created
                    _logger.info(f"🔍 Verificando si el archivo fue creado: {backup_path}")
                    _logger.info(f"🔍 File exists: {os.path.exists(backup_path)}")
                    
                    if os.path.exists(backup_path):
                        file_size = os.path.getsize(backup_path)
                        _logger.info(f"� Tamaño del archivo: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
                        _logger.info(f"� Permisos del archivo: {oct(os.stat(backup_path).st_mode)}")
                        _logger.info(f"📂 Contenido del directorio: {os.listdir(backup_dir)}")
                        
                        # Let's copy to a permanent location if using temp
                        final_path = backup_path
                        if backup_dir != self.storage_path:
                            try:
                                # Try to copy to original storage path
                                import shutil
                                final_destination = os.path.join(self.storage_path, backup_filename)
                                os.makedirs(self.storage_path, exist_ok=True)
                                shutil.copy2(backup_path, final_destination)
                                final_path = final_destination
                                _logger.info(f"📋 Archivo copiado a ubicación final: {final_path}")
                            except Exception as copy_error:
                                _logger.warning(f"⚠️ No se pudo copiar a la ubicación final: {copy_error}")
                                final_path = backup_path
                        
                        message = f"Backup saved successfully to server: {final_path} ({file_size} bytes)"
                        self.message_post(body=message, subject="Server Backup Success")
                        
                        # Create backup detail record with correct URL path
                        self.env['backup.process.detail'].create({
                            'backup_process_id': self.id,
                            'backup_date_time': datetime.now(),
                            'file_name': backup_filename,
                            'url': final_path,  # Store the actual file path for download
                            'message': f'Backup created successfully at {final_path}',
                            'status': 'Success',
                            'backup_location': 'local'
                        })
                        
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': 'Server Backup Success!',
                                'message': message,
                                'type': 'success',
                            }
                        }
                    else:
                        raise UserError("Backup file was not created successfully")
                else:
                    raise UserError(f"pg_dump failed: {result.stderr}")
                
        except Exception as e:
            error_message = f"Failed to create server backup: {str(e)}"
            self.message_post(body=error_message, subject="Server Backup Error")
            raise UserError(error_message)
    
    @api.model
    def ignite_backup_server_crone(self):
        """
            Crone method to call functions either to create a new cron, or to update a existing one
        """

        current_time = datetime.now()
        processes = self.env['backup.process'].sudo().search([('backup_starting_time', '<=', current_time), ('state', '=', 'confirm')])
        for process in processes:
            process.create_backup_request()
        upt_processes = self.env['backup.process'].sudo().search([('backup_starting_time', '<=', current_time), ('state', '=', 'running'), ('update_requested', '=', True)])        
        for upt_process in upt_processes:
            if upt_process.update_requested:
                upt_process.update_backup_request()
        
        # Functionality to send the mails to the admin for failed backups.
        confirmed_processes = self.env['backup.process'].sudo().search([('state', '=', 'running')])
        time_now = datetime.now()
        yesterday = time_now - relativedelta(days=1)
        failed_backups = confirmed_processes.mapped('backup_details_ids').filtered(lambda p: p.status=='Failure' and p.backup_date_time >= yesterday)
        if failed_backups:
            _logger.info("========== failed_backups ======= %r", failed_backups)
            self.send_backup_failure_mail(failed_backups)
        
    
    
    def get_odoo_admins(self):
        """
            Method to list the odoo admins.
        """
        admin_list = []
        users = self.env['res.users'].sudo().search([])
        for user in users:
            if user.has_group('base.group_system'):
                admin_list.append(user.partner_id.id)
        return admin_list
            
    def send_backup_failure_mail(self, failed_backups):
        """
            Method to send the backup failure mail to the admin users.
        """
        for obj in failed_backups:
            admin_list = self.get_odoo_admins()
            template = self.env.ref('wk_backup_restore.backup_failure_template')
            email_values = {"recipient_ids":admin_list}
            mail_id = template.send_mail(obj.id, force_send=True, email_values=email_values)
            current_mail = self.env['mail.mail'].browse(mail_id)
            current_mail.send()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('backup.process')
            res = super(BackupProcess, self).create(vals)
        return res
    
    def write(self, vals):
        if self.state not in ['draft','cancel','confirm'] and self.backup_starting_time <= datetime.now() and not vals.get('update_requested') == False:
            vals['update_requested'] = True
        return super(BackupProcess, self).write(vals)


    def unlink(self):
        if self.state not in ['draft','cancel','confirm']:
            raise UserError("Not allowed")
        return super(BackupProcess, self).unlink()


    def confirm_process(self):
        """
            Called by the Confirm button over the backup process record
        """

        if self.state == 'draft':
            # Raise error if master password is not set in odoo conf file
            if not config.get('master_passwd', False):
                raise UserError("Master password parameter(master_passwd) not set in Odoo conf file!!")

            # Creating the backup log file if doesn't exists
            if not os.path.exists(manage_backup_crons.LOG_FILE_PATH):
                _logger.info("========== Creating Backup Log File ==========")
                fp = open(manage_backup_crons.LOG_FILE_PATH, 'x')
                fp.close()

            if self.backup_location == 'remote':
                self.validate_remote_backup()
            
            self.state = "confirm"
            
            # Automatically create backup cron and set to running
            self.create_backup_request()

        elif self.state == 'confirm':
            # If already confirmed, create the backup cron
            self.create_backup_request()

    def cancel_process(self):
        """
            Called by the Cancel button over the backup process record
        """

        if self.state in ['draft','confirm']:
            self.state ="cancel"
            
    @api.model
    def remove_old_backups(self):
        """
            Cron method to call functions to remove the backup file of the backup processes
        """
        
        processes = self.env['backup.process'].sudo().search([('state', '=', 'running'),('enable_retention', '=', True)])
        for rec in processes:
            details_ids = rec.backup_details_ids.filtered(lambda d: d.status == "Success").sorted(key=lambda p:p.id)
            if details_ids:
                end_index = len(details_ids) - rec.retention
                if end_index>0:
                    updated_details_ids = details_ids[:end_index]
                    rec.remove_backup_files(updated_details_ids)
    
    def remove_backup_files(self, bkp_details_ids):
        """
            Method to check if the backup file exist, and if exist then remove that backup file.
            Also, updates the status and the message of the backup process details.
            
            Args:
                bkp_details_ids ([object]): [all the backup process ids whose backup file needs to be deleted.]
        """
        try:
            msg = None
            for bkp in bkp_details_ids:
                backup_location = self.backup_location
                if hasattr(self,'_remove_%s_backup_files'%backup_location):## if you want to update dictionary then you can define this function _remove_{backup_location}_backup_files
                    msg = getattr(self,'_remove_%s_backup_files'%backup_location)(bkp)
                _logger.info("---- %r -- ", msg)
            return True
        except Exception as e:
            _logger.error("Database backup remove error: " + str(e))
            return False
        
        
    def _remove_local_backup_files(self, bkp_details_id):
        """
            Method to check if the backup file exist on the main server, 
            and if exist then remove that backup file.
        """
        msg = None
        if os.path.exists(bkp_details_id.url):
            res = os.remove(bkp_details_id.url)
            msg = 'Database backup dropped successfully  at ' + datetime.now().strftime("%m-%d-%Y-%H:%M:%S") + " after retention."
            bkp_details_id.message = msg
            bkp_details_id.status = "Dropped"
        else:
            msg = "Database backup file doesn't exists."
            bkp_details_id.message = msg
            bkp_details_id.status = "Failure"

        return msg
    
    
    def _remove_remote_backup_files(self, bkp_details_id):
        """
            Method to check if the backup file exist on the remote backup server, 
            and if exist then remove that backup file.
        """
        msg = None
        ssh_obj = self.login_remote()
        if self.check_remote_backup_existance(ssh_obj, bkp_details_id.url):
            sftp = ssh_obj.open_sftp()
            sftp.remove(bkp_details_id.url)
            sftp.close()
            msg = 'Database backup dropped successfully  at ' + datetime.now().strftime("%m-%d-%Y-%H:%M:%S") + " after retention from remote server."
            bkp_details_id.message = msg
            bkp_details_id.status = "Dropped"
        else:
            msg = "Database backup file doesn't exists on remote server."
            bkp_details_id.message = msg
            bkp_details_id.status = "Failure"
        
        return msg
    
    def login_remote(self):
        """
            Method to login to the remote backup server using SSH.
            
        Returns:
            [Object]: [Returns SSh object if connected successfully to the remote server.]
        """
        try:
            import paramiko
            ssh_obj = paramiko.SSHClient()
            ssh_obj.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_obj.connect(hostname=self.remote_server_id.sftp_host, username=self.remote_server_id.sftp_user, password=self.remote_server_id.sftp_password, port=self.remote_server_id.sftp_port)
            return ssh_obj
        except ImportError:
            raise UserError("paramiko module not found. Please install it using pip: pip3 install paramiko")
        except Exception as e:
            _logger.info(f"==== Exception while connecting to remote server ==== {e} ===")
            return False
    
    def test_host_connection(self):
        if self.remote_server_id:
            response = self.validate_remote_backup()
            if response:
                message = self.env['backup.custom.message.wizard'].create({'message':"Connection successful!"})
                action = self.env.ref('wk_backup_restore.action_backup_custom_message_wizard').read()[0]
                action['res_id'] = message.id
                return action
    
    
    def validate_remote_backup(self):
        """
            Method to validate the remote backup process.
            It checks the connection to remote server along with the existance of backup 
            storage path on the remote server.
        """
        ssh_obj = self.login_remote()
        if ssh_obj:
            backup_dir = self.storage_path
            cmd = "ls %s"%(backup_dir)
            check_path = self.execute_on_remote_shell(ssh_obj,cmd)
            if check_path and not check_path.get('status'):
                raise UserError(f"Storage path doesn't exist on remote server. Please create the mentioned backup path on the remote server. Error: {check_path.get('message')}")

            cmd = f"touch {backup_dir}/test.txt"
            create_file = self.execute_on_remote_shell(ssh_obj,cmd)
            if create_file and not create_file.get('status'):
                raise UserError(f"The mentioned ssh user doesn't have rights to create file. Please provide required permissions on the default backup path. Error: {create_file.get('message')}")
            else:
                cmd = f"rm {backup_dir}/test.txt"
                delete_file = self.execute_on_remote_shell(ssh_obj,cmd)
                if delete_file and delete_file.get('status'):
                    _logger.info("======== Backup Directory Permissions Checked Successfully =========")

        else:
            raise UserError("Couldn't connect to the remote server.")

        return True


    def check_remote_backup_existance(self, ssh_obj, bkp_path):
        """
            Method to check the existance of the backup file on the remote server.
            Args:
                ssh_obj ([object]): [SSH Object of the remote server.]
                bkp_path ([object]): [Path of the backup file on the remote server.]
        """
        cmd = "ls -f %s"%(bkp_path)
        check_path = self.execute_on_remote_shell(ssh_obj,cmd)
        if check_path and not check_path.get('status'):
            _logger.error(f"-----------Database Backup file '{bkp_path}' doesn't exist on remote server.--------")
            return False
        return True
    
    
    
    def execute_on_remote_shell(self, ssh_obj,command):
        """
            Method to execute the command on the remote server.
        """
        _logger.info(command)
        response = dict()
        try:
            ssh_stdin, ssh_stdout, ssh_stderr = ssh_obj.exec_command(command)
            # _logger.info(ssh_stdout.readlines())
            res = ssh_stdout.readlines()
            _logger.info("execute_on_remote_shell res: %r", res)
            _logger.info("execute_on_remote_shell err: ")
            err = ssh_stderr.readlines()
            _logger.info(err)
            if err:
                response['status'] = False
                response['message'] = err
                return response
            response['status'] = True
            response['result'] = res
            return response
        except Exception as e:
            _logger.info("+++ERROR++",command)
            _logger.info("++++++++++ERROR++++",e)
            response['status'] = False
            response['message'] = e
            return response

    def run_automatic_backup(self):
        """Método que ejecuta backup automático cada 8 horas para todos los procesos en estado 'running'"""
        _logger.info("=== Ejecutando backup automático cada 8 horas ===")
        
        # Buscar todos los procesos de backup en estado 'running'
        running_processes = self.search([('state', '=', 'running')])
        
        if not running_processes:
            _logger.info("No hay procesos de backup activos para ejecutar")
            return
            
        _logger.info(f"Encontrados {len(running_processes)} procesos de backup activos")
        
        for process in running_processes:
            try:
                _logger.info(f"🔄 Ejecutando backup automático para proceso: {process.name}")
                _logger.info(f"📁 Storage Path del proceso: {process.storage_path}")
                _logger.info(f"🗃️ Base de datos: {process.db_name}")
                _logger.info(f"📦 Formato: {process.backup_format}")
                
                # Ejecutar el backup usando el método save_backup_to_server (no download)
                result = process.save_backup_to_server()
                
                _logger.info(f"✅ Backup automático completado exitosamente para proceso: {process.name}")
                _logger.info(f"📊 Resultado del backup: {result}")
                
            except Exception as e:
                _logger.error(f"❌ Error en backup automático para proceso {process.name}: {str(e)}")
                import traceback
                _logger.error(f"🔍 Traceback completo: {traceback.format_exc()}")
                
        _logger.info("=== Backup automático completado ===")
        return True
