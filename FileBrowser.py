import asyncio
import time
import os.path
import mimetypes
import argparse
import re


async def dispatch(reader, writer):
    message = ''
    while True:
        data = await reader.readline()
        message += data.decode()
        if data == b'\r\n':
            break

    request = parse_request_header(message)

    header, content = get_response_message(request)
    a = []
    a.append(bytes(header, 'utf-8'))
    b = []
    b.append(content)
    writer.writelines(a)
    writer.writelines(b)
    await writer.drain()

    writer.close()


def handle_path(str):
    return str.replace('/', '\\')


def handle_url(str):
    return str.replace(' ', '%20')


def reverse_handle_url(str):
    return str.replace('%20', ' ')


def good_response(request):
    origin_path = reverse_handle_url(request['path'])
    request_path = handle_path(origin_path)
    request_full_path = root_dir + request_path

    response_start_line = "HTTP/1.0 200 OK\r\n"
    response_headers = "Server:file server\r\nConnection: close\r\n\r\n"

    response_front = "<html><head><title>hello head</title></head><body>"

    response_after = "<HR></body></html>"
    response_html_body = ""
    if os.path.isdir(request_full_path):
        response_h1_title = "<h1>Index of " + origin_path + "</h1><HR>"
        file_list = os.listdir(request_full_path)
        if (origin_path != '/'):
            response_html_body += "<a href=.."  + "/>../</a><br>"
        for i in file_list:
            if os.path.isdir(request_full_path + str(i)):
                response_html_body += "<a href=" + origin_path + handle_url(str(i)) + "/>" + str(i) + "/</a><br>"
            else:
                response_html_body += "<a href=" + origin_path + handle_url(str(i)) + ">" + str(i) + "</a><br>"


        final_header = response_start_line + response_headers
        final_file = response_front + response_h1_title + response_html_body + response_after
        return final_header, bytes(final_file, 'utf-8')

    elif os.path.isfile(request_full_path):
        try:
            file = open(request_full_path, 'rb')
        except FileNotFoundError:
            return bad_request(404)
        response_headers = "Server:file server\r\nConnection: close\r\n"

        if request.__contains__('Range'):
            response_start_line = "HTTP/1.0 206 OK\r\n"
            size = os.path.getsize(request_full_path)
            start, end = handle_range(request['Range'], size=size)
            response_headers += 'Accept-Ranges: bytes\r\n' + 'Content-Range:bytes=' + str(start) + '-' + str(
                end) + '\r\n'
            final_file = file.read()[start:end + 1]
        else:

            final_file = file.read()

        mime_type = mimetypes.guess_type(url=request_full_path, strict=False)
        response_headers += "Content-type: " + str(mime_type[0]) + '\r\n\r\n'
        final_header = response_start_line + response_headers

        return final_header, final_file
    else:
        print(request_full_path)
        return bad_request(404)


def handle_range(str, size):
    tmp = re.split('=', str)[1]

    if tmp[0] == '-':
        return size - int(tmp[1:]), size - 1
    elif tmp[len(tmp) - 1] == '-':
        return int(tmp[0:len(tmp) - 1]), size - 1
    else:
        lst = re.split('-', tmp)
        return int(lst[0]), int(lst[1])


def bad_request(status_code):
    response_start_line = ''
    response_body = ''
    if status_code == 405:
        response_start_line = "HTTP/1.0 405 Method Not Allowed\r\nConnection: closed\r\n"
        response_body = "<html><head><title>hello head</title></head><body><h1>405 Method Not Allowed<HR></h1></body>"
    elif status_code == 404:
        response_start_line = "HTTP/1.0 404 Not Found\r\nConnection: closed\r\n"
        response_body = "<html><head><title>hello head</title></head><body><h1>404 not found</h1><HR></body>"
    response_headers = "Server:file server\r\n\r\n"

    final_header = response_start_line + response_headers
    final_file = response_body
    return final_header, bytes(final_file, 'utf-8')


def get_response_message(request):
    request_method = request['command']
    if request_method == 'GET' or request_method == 'HEAD':
        return good_response(request)
    else:
        if request_method == 'POST':
            time.sleep(2)
        return bad_request(405)


def parse_request_header(header):
    message_split = re.split(" |\\r\\n", header)
    dict = {'command': message_split[0], 'path': message_split[1], 'version': message_split[2]}
    message_split = re.split(": | |\\r\\n", header)
    for i in range(0, len(message_split)):
        if message_split[i] == 'Range':
            dict[message_split[i]] = message_split[i + 1]

    return dict


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simple Web File Browser')
    parser.add_argument('--port', type=int, default=8080, help='an integer for the port of the simple web file browser')
    parser.add_argument('--dir', type=str, default="./",
                        help='The Directory that the browser should display for home page')
    args = parser.parse_args()
    root_dir = os.path.abspath(args.dir)
    port = args.port

    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(dispatch, '127.0.0.1', port, loop=loop)
    server = loop.run_until_complete(coro)

    try:
        loop.run_forever()
    except Exception:
        print(Exception)

    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
