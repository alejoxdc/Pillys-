# BACKUP ODOO DATABASES & FILESTORE

**Available Odoo Backup DB/Filestore Modes:**

* **Local**
* **Remote Server**
* **Google Drive**
* **Dropbox**
* **Amazon S3**

**Module For backup ODOO databases and automating the backup process of ODOO.**

* Multiple Backup Modes: The tool allows the user to use multiple backup modes at the same time.
* **Filestore** Backup: The tool can backup the filestore.
* ODOO Databases Backup: The tool can backup ODOO databases in a specified path.
* Detailed Message Log: The tool provides a detailed log of messages during the backup process.
* Backup Status Information and History: The tool provides information about the status of the backup and maintains a history of past backups.
* User-selectable Format: The user can select the format to use when dumping the database, including a custom archive, plain text SQL, or tar archive.
* Archive Backup Process: The tool includes an archive backup process.
* Repeat Missed Backup Process: The tool can repeat the backup process if it was missed for any reason.

# Features

* Dump the ODOO database in a specified format
* Zip the filestore in a specified location
* Output a custom archive that can be used with pg_restore and is compressed with gzip
* Output a plain-text SQL script file
* Output a tar archive that can be used with pg_restore and is compressed with gzip
* Backup the filestore
* Allow for multiple backup modes to be used at the same time

### Tech

Odoo Auto Backup Module uses

* [PYTHON](https://www.python.org/) - Models
* [XML](https://www.w3.org/XML/) - Views
* [HTML](https://www.w3.org/html/) - UI
* [Twitter Bootstrap](https://getbootstrap.com/2.3.2/) - UI
* [backbone.js](http://backbonejs.org/) - Views
* [jQuery](https://jquery.com/)
* [PSQL](https://www.postgresql.org/) - DB

### External Dependencies

`pip depends on your python version / mapped pip version.`

* [PYSFTP](https://pypi.org/project/pysftp/) `pip install pysftp`
* [Dropbox](https://pypi.org/project/dropbox/) `pip install dropbox`
* [Progress Meter](https://pypi.org/project/tqdm/) `pip install tqdm`
* [Boto3](https://pypi.org/project/boto3/) `pip install boto3`
* [Botocore](https://pypi.org/project/botocore/) `pip install botocore`
* [Simplejson](https://pypi.org/project/simplejson/) `pip install simplejson`

### Installation

To install the ODOO and Auto Backup module and configure backup, you can follow these steps:

* Install ODOO: Follow the installation instructions for your operating system to install ODOO.
* Install the Auto Backup module: Find the Auto Backup module in the ODOO App Store and install it.
* Configure backup: Go to the "General Settings" menu in ODOO and configure the backup settings as desired.
* Start the backup process: Once you have configured the backup settings, the backup process will start according to the schedule you have set. You can view the backup status and history in the Auto Backup menu.

### CHANGELOGS

> Date: 07/12/2020

* Performance Improvement
* Session Upload Trace For Dropbox Files > 150 mb
* Full Metadata Track In Message Logs
* Fix Dropbox Tar files upload
* Progress Meter In Logs

> Date: 22/11/2020

* Amazon S3 Database Backup
* Amazon S3 Filestore Backup

> Date: 25/12/2022

* GDRIVE Client Update: There has been an update to the GDRIVE client.
* New Format Named DUMP: A new format named DUMP has been added, which allows the user to get a backup with both the filestore and database dump zipped.
* Documentation: The documentation for the backup configuration views has been improved.

### Todos

* Backup Dashboard

### Author

[Hilar AK](https://www.linkedin.com/in/hilar-ak/) `https://www.linkedin.com/in/hilar-ak/`

### Git Repository

[Hilar AK](https://github.com/hilarak) `hilarak@gmail.com`
