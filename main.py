#!/usr/bin/env python3
import argparse
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('service_account_file', type=str, help='Service Account file in json format')
    parser.add_argument('package_name', type=str, help='Package Name of the app bundle')
    parser.add_argument('aab_file', type=str, help='Path of the Android App Bundle file')
    parser.add_argument('track', choices=['production', 'alpha', 'beta', 'internal'], default='internal',
                        help='Track to upload the apk to')
    args = parser.parse_args()

    credentials = service_account.Credentials.from_service_account_file(
        args.service_account_file,
        scopes=['https://www.googleapis.com/auth/androidpublisher']
    )

    service = build('androidpublisher', 'v3', credentials=credentials)

    edit_id = None
    try:
        edit_request = service.edits().insert(body={}, packageName=args.package_name)
        result = edit_request.execute()
        edit_id = result['id']

        aab_response = service.edits().bundles().upload(
            editId=edit_id,
            packageName=args.package_name,
            media_mime_type='application/octet-stream',
            media_body=args.aab_file).execute()
        print(f'✓ Android App Bundle with version code {aab_response["versionCode"]} has been uploaded')

        track_response = service.edits().tracks().update(
            editId=edit_id,
            track=args.track,
            packageName=args.package_name,
            body={
                'releases': [{
                    'versionCodes': [aab_response['versionCode']],
                    'status': 'completed'
                }]
            }).execute()
        print(f'✓ Track {args.track} is set for version code(s) {track_response["releases"]}')

        commit_request = service.edits().commit(
            editId=edit_id, packageName=args.package_name).execute()

        print(f'✓ Edit #{commit_request["id"]} has been committed')
        
    except HttpError as e:
        if edit_id:
            try:
                service.edits().delete(editId=edit_id, packageName=args.package_name).execute()
            except:
                pass
        
        error_message = str(e)
        
        if 'Version code' in error_message and 'has already been used' in error_message:
            import re
            match = re.search(r'Version code (\d+) has already been used', error_message)
            if match:
                version = match.group(1)
                print(f'\n✗ Error: Version code {version} has already been used.', file=sys.stderr)
                print(f'  Please increment the versionCode in your app/build.gradle file.', file=sys.stderr)
                sys.exit(1)
        
        print(f'\n✗ Upload failed: {e._get_reason()}', file=sys.stderr)
        sys.exit(1)
        
    except Exception as e:
        if edit_id:
            try:
                service.edits().delete(editId=edit_id, packageName=args.package_name).execute()
            except:
                pass
        print(f'\n✗ Unexpected error: {e}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
