"""
Getting files from/to the OS X VM can be a pain. This is a simple webserver
to allow posting a file.
"""

import os
import asgish


@asgish.to_asgi
async def handler(request):
    assert request.method == 'POST'
    filename2 = request.path.strip('/')
    filename1 = filename2 + '.part'
    assert '/' not in filename1
    with open(filename1, 'wb') as f:
        async for chunk in request.iter_body():
            f.write(chunk)
    if os.path.isfile(filename2):
        os.remove(filename2)
    os.rename(filename1, filename2)
    print("received", filename2)
    return "Success!"

if __name__ == '__main__':
    asgish.run(handler, 'uvicorn', '0.0.0.0:80')
