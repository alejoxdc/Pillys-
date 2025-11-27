import os
import logging
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BackupAutoScp(models.Model):
    _name = 'backup.auto.scp'
    _description = 'Backup Automático SCP'
    _order = 'create_date desc'

    name = fields.Char('Nombre del Backup', required=True, default='Backup Automático')
    database_name = fields.Char('Base de Datos', required=True, default=lambda self: self.env.cr.dbname)
    
    # Configuración del servidor local Odoo
    local_odoo_host = fields.Char('Host Odoo Local', default='paramo.lago.digital', required=True, 
                                  help='IP o dominio donde corre Odoo (localhost, paramo.lago.digital, etc.)')
    local_odoo_port = fields.Char('Puerto Odoo Local', default='443', required=True,
                                  help='Puerto donde corre Odoo (80, 443, 8069, etc.)')
    master_password = fields.Char('Master Password', default='Alejandro88.**', required=True,
                                  help='Master password configurado en odoo.conf')
    
    # Configuración del servidor remoto
    server_host = fields.Char('Servidor SSH', default='5.78.131.185', required=True)
    server_user = fields.Char('Usuario SSH', default='root', required=True)
    server_password = fields.Char('Password SSH', default='xApgsicXgqmX', required=True)
    server_path = fields.Char('Ruta en Servidor', default='/home/a.fecol.digital/odoo17/backups', required=True)
    ssh_key_path = fields.Char('Ruta Clave SSH', default='/root/.ssh/id_rsa_backup', help='Ruta a la clave privada SSH')
    
    # Configuración de frecuencia
    backup_frequency = fields.Selection([
        ('2_minutes', 'Cada 2 minutos (PRUEBA)'),
        ('8_hours', 'Cada 8 horas'),
        ('daily', 'Diario'),
        ('manual', 'Solo manual')
    ], default='2_minutes', string='Frecuencia', required=True)
    
    # Estados y logs
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('active', 'Activo'),
        ('inactive', 'Inactivo')
    ], default='draft', string='Estado')
    
    last_backup_date = fields.Datetime('Último Backup')
    next_backup_date = fields.Datetime('Próximo Backup')
    backup_count = fields.Integer('Total de Backups', default=0)
    
    # Log de resultados
    last_backup_result = fields.Text('Resultado del Último Backup')
    last_backup_size = fields.Char('Tamaño del Último Backup')
    last_backup_file = fields.Char('Último Archivo Creado')
    
    # Variables para control (sin hilos)

    def _get_default_db_name(self):
        return self.env.cr.dbname

    @api.model
    def create(self, vals):
        if not vals.get('database_name'):
            vals['database_name'] = self.env.cr.dbname
        return super().create(vals)

    def action_activate(self):
        """Activar el backup automático"""
        self.ensure_one()
        self.state = 'active'
        self._schedule_next_backup()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Backup Activado',
                'message': f'Backup automático activado. Próximo backup: {self.next_backup_date}\\nEl cron ejecutará backups cada 2 minutos',
                'type': 'success'
            }
        }

    def action_deactivate(self):
        """Desactivar el backup automático"""
        self.ensure_one()
        self.state = 'inactive'
        self.next_backup_date = False
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '⏹️ Backup Desactivado',
                'message': 'Backup automático desactivado.',
                'type': 'warning'
            }
        }

    def action_backup_manual(self):
        """Ejecutar backup manual inmediatamente"""
        self.ensure_one()
        try:
            # Verificar que tengamos la configuración básica
            if not all([self.server_host, self.server_user, self.server_password, self.server_path]):
                raise Exception("Configuración incompleta. Complete todos los campos del servidor SSH.")
            
            result = self._execute_backup_scp()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '🎉 Backup Manual Exitoso',
                    'message': result.get('message', 'Backup completado correctamente'),
                    'type': 'success',
                    'sticky': True
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '❌ Error en Backup Manual',
                    'message': f'Error: {str(e)}',
                    'type': 'danger',
                    'sticky': True
                }
            }

    def _schedule_next_backup(self):
        """Programar el próximo backup"""
        if self.backup_frequency == '2_minutes':
            self.next_backup_date = datetime.now() + timedelta(minutes=2)
        elif self.backup_frequency == '8_hours':
            self.next_backup_date = datetime.now() + timedelta(hours=8)
        elif self.backup_frequency == 'daily':
            self.next_backup_date = datetime.now() + timedelta(days=1)
        else:
            self.next_backup_date = False

# Métodos de hilo eliminados - usando solo cron

    def _execute_backup_scp(self):
        """Ejecutar backup y enviarlo por SCP"""
        _logger.info("🚀 INICIANDO BACKUP AUTOMÁTICO SCP")
        
        # Usar nombre fijo para sobrescribir archivo existente
        backup_filename = f"backup_{self.database_name}.zip"
        remote_file_path = f"{self.server_path}/{backup_filename}"
        
        try:
            # PASO 1: Crear directorio remoto
            mkdir_cmd = f"sshpass -p '{self.server_password}' ssh -o StrictHostKeyChecking=no {self.server_user}@{self.server_host} 'mkdir -p {self.server_path}'"
            _logger.info("📁 Creando directorio remoto: %s", self.server_path)
            
            mkdir_result = os.system(mkdir_cmd)
            if mkdir_result != 0:
                raise Exception(f"Error creando directorio remoto (código: {mkdir_result})")
            
            # PASO 2: Crear backup y enviarlo DIRECTAMENTE al servidor
            protocol = "https" if self.local_odoo_port == "443" else "http"
            backup_url = f"{protocol}://{self.local_odoo_host}:{self.local_odoo_port}/web/database/backup"
            
            # Comando que crea el backup y lo envía directamente por SSH (sin usar espacio local)
            scp_cmd = f"curl -X POST -d 'master_pwd={self.master_password}&name={self.database_name}&backup_format=zip' {backup_url} | sshpass -p '{self.server_password}' ssh -o StrictHostKeyChecking=no {self.server_user}@{self.server_host} 'cat > {remote_file_path}'"
            
            _logger.info("📤 ENVIANDO BACKUP DIRECTO AL SERVIDOR (SIN USAR ESPACIO LOCAL)")
            _logger.info("🔗 Ejecutando: curl -> ssh con clave -> servidor")
            
            # Ejecutar el comando
            scp_result = os.system(scp_cmd)
            
            if scp_result == 0:
                # PASO 3: Verificar tamaño del archivo en el servidor
                size_cmd = f"sshpass -p '{self.server_password}' ssh -o StrictHostKeyChecking=no {self.server_user}@{self.server_host} 'ls -lh {remote_file_path} | cut -d\" \" -f5'"
                size_output = os.popen(size_cmd).read().strip()
                
                # Actualizar registros
                self.write({
                    'last_backup_date': datetime.now(),
                    'backup_count': self.backup_count + 1,
                    'last_backup_result': f'✅ Backup exitoso enviado a {self.server_host}:{remote_file_path}',
                    'last_backup_size': size_output or 'Desconocido',
                    'last_backup_file': backup_filename
                })
                
                # Programar próximo backup si está activo
                if self.state == 'active':
                    self._schedule_next_backup()
                
                _logger.info("🎉 BACKUP SCP COMPLETADO EXITOSAMENTE")
                _logger.info("📁 Archivo: %s", remote_file_path)
                _logger.info("📏 Tamaño: %s", size_output)
                
                return {
                    'success': True,
                    'message': f'✅ Backup enviado a {self.server_host}\n📁 Archivo: {backup_filename}\n📏 Tamaño: {size_output}',
                    'file': backup_filename,
                    'size': size_output
                }
                
            else:
                raise Exception(f"Error en SCP (código: {scp_result})")
                
        except Exception as e:
            error_msg = f"❌ Error en backup SCP: {str(e)}"
            _logger.error(error_msg)
            
            self.write({
                'last_backup_result': error_msg,
                'last_backup_size': 'Error',
                'last_backup_file': 'Error'
            })
            
            raise UserError(error_msg)

    @api.model
    def cron_auto_backup(self):
        """Método para el cron automático cada 2 minutos - USA CONFIGURACIÓN DEL USUARIO"""
        _logger.info("🕐 EJECUTANDO CRON DE BACKUP AUTOMÁTICO CADA 2 MINUTOS")
        
        # Buscar configuración activa del usuario
        active_backup = self.search([('state', '=', 'active')], limit=1)
        if not active_backup:
            _logger.warning("⚠️ No hay configuración de backup activa")
            return
            
        try:
            # Usar configuración del usuario
            backup_filename = f"backup_{active_backup.database_name}.zip"
            remote_file_path = f"{active_backup.server_path}/{backup_filename}"
            
            _logger.info("📁 Creando backup: %s", backup_filename)
            
            # PASO 1: Crear directorio remoto
            mkdir_cmd = f"sshpass -p '{active_backup.server_password}' ssh -o StrictHostKeyChecking=no {active_backup.server_user}@{active_backup.server_host} 'mkdir -p {active_backup.server_path}'"
            mkdir_result = os.system(mkdir_cmd)
            if mkdir_result != 0:
                raise Exception(f"Error creando directorio remoto (código: {mkdir_result})")
            
            # PASO 2: Crear backup y enviarlo DIRECTAMENTE al servidor
            protocol = "https" if active_backup.local_odoo_port == "443" else "http"
            backup_url = f"{protocol}://{active_backup.local_odoo_host}:{active_backup.local_odoo_port}/web/database/backup"
            scp_cmd = f"curl -X POST -d 'master_pwd={active_backup.master_password}&name={active_backup.database_name}&backup_format=zip' {backup_url} | sshpass -p '{active_backup.server_password}' ssh -o StrictHostKeyChecking=no {active_backup.server_user}@{active_backup.server_host} 'cat > {remote_file_path}'"
            
            _logger.info("📤 ENVIANDO BACKUP DIRECTO AL SERVIDOR")
            scp_result = os.system(scp_cmd)
            
            if scp_result == 0:
                # Verificar tamaño del archivo
                size_cmd = f"sshpass -p '{active_backup.server_password}' ssh -o StrictHostKeyChecking=no {active_backup.server_user}@{active_backup.server_host} 'ls -lh {remote_file_path} | cut -d\" \" -f5'"
                size_output = os.popen(size_cmd).read().strip()
                
                _logger.info("🎉 BACKUP CRON COMPLETADO EXITOSAMENTE")
                _logger.info("📁 Archivo: %s", remote_file_path)
                _logger.info("📏 Tamaño: %s", size_output)
            else:
                raise Exception(f"Error en SCP (código: {scp_result})")
                
        except Exception as e:
            _logger.error("❌ Error en backup cron: %s", str(e))
        
        _logger.info("🏁 CRON DE BACKUP AUTOMÁTICO TERMINADO")