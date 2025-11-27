## Upload Backup

[Session Start]

Upload sessions allow you to upload a single file in one or more requests, for example where the size of the file is
greater than 150 MB. This call starts a new upload session with the given data. You can then use upload_session/append:2
to add more data and upload_session/finish to save all the data to a file in Dropbox.
A single request should not upload more than 150 MB. The maximum size of a file one can upload to an upload session is
350 GB.
An upload session can be used for a maximum of 48 hours. Attempting to use an UploadSessionStartResult.session_id with
upload_session/append:2 or upload_session/finish more than 48 hours after its creation will return a
UploadSessionLookupError.not_found.
Calls to this endpoint will count as data transport calls for any Dropbox Business teams with a limit on the number of
data transport calls allowed per month. For more information, see the Data transport limit page.

#### Append Data to upload in a session

[Append Data To The Session]

Append more data to an upload session.
When the parameter close is set, this call will close the session.
A single request should not upload more than 150 MB. The maximum size of a file one can upload to an upload session is
350 GB.
Calls to this endpoint will count as data transport calls for any Dropbox Business teams with a limit on the number of
data transport calls allowed per month. For more information, see the Data transport limit page.

#### Session Finish

[Session Finish]

Finish an upload session and save the uploaded data to the given file path.
A single request should not upload more than 150 MB. The maximum size of a file one can upload to an upload session is
350 GB.
Calls to this endpoint will count as data transport calls for any Dropbox Business teams with a limit on the number of
data transport calls allowed per month. For more information, see the Data transport limit page.

## List files in a directory

[List Folder Contents]

Starts returning the contents of a folder. If the result's ListFolderResult.has_more field is true, call
list_folder/continue with the returned ListFolderResult.cursor to retrieve more entries.
If you're using ListFolderArg.recursive set to true to keep a local cache of the contents of a Dropbox account, iterate
through each entry in order and process them as follows to keep your local state in sync:
For each FileMetadata, store the new entry at the given path in your local state. If the required parent folders don't
exist yet, create them. If there's already something else at the given path, replace it and remove all its children.
For each FolderMetadata, store the new entry at the given path in your local state. If the required parent folders don't
exist yet, create them. If there's already something else at the given path, replace it but leave the children as they
are. Check the new entry's FolderSharingInfo.read_only and set all its children's read-only statuses to match.
For each DeletedMetadata, if your local state has something at the given path, remove it and all its children. If
there's nothing at the given path, ignore this entry.
Note: auth.RateLimitError may be returned if multiple list_folder or list_folder/continue calls with same parameters are
made simultaneously by same API app for same user. If your app implements retry logic, please hold off the retry until
the previous request finishes.

## Delete Batch Of Files

[Remove Batch Of Files]

Delete multiple files/folders at once.
This route is asynchronous, which returns a job ID immediately and runs the delete batch asynchronously. Use
delete_batch/check to check the job status.


[Session Start]: https://www.dropbox.com/developers/documentation/http/documentation#files-upload_session-start

[Append Data To The Session]: https://www.dropbox.com/developers/documentation/http/documentation#files-upload_session-append

[Session Finish]: https://www.dropbox.com/developers/documentation/http/documentation#files-upload_session-finish

[List Folder Contents]: https://www.dropbox.com/developers/documentation/http/documentation#files-list_folder

[Remove Batch Of Files]: https://www.dropbox.com/developers/documentation/http/documentation#files-delete_batch