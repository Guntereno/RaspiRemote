from http.server import BaseHTTPRequestHandler, HTTPServer
from posixpath import relpath
from urllib.parse import urlparse
import gphoto2 as gp
import os
import traceback

# Set of 'capturetarget' choices we expect to save the image to the camera
memory_card_choices = {
    "Memory card"
}

mime_types = {
    ".css": "text/css",
    ".js": "text/javascript",
    ".htm": "text/html",
    ".ico": "image/x-icon"
}

public_path = os.path.join(os.path.dirname(
    os.path.realpath(__file__)), "Public")


def get_mime_type(path):
    extension = os.path.splitext(path)[1]
    if extension in mime_types:
        return mime_types[extension]
    return "text/plain"


def exception_to_string(e):
    return f'"{type(e)}" exception occured with message "{str(e)}"'


def do_capture():
    status = 0
    message = ""
    try:
        camera = gp.Camera()
        camera.init()
        ensure_captures_to_memory_card(camera)
        file_path = camera.capture(gp.GP_CAPTURE_IMAGE)
        status = 200
        message = 'Captured to: {0}/{1}'.format(
            file_path.folder, file_path.name)

    except Exception as e:
        status = 500
        message = exception_to_string(e)
        traceback.print_exc()
    finally:
        camera.exit()

    return status, message


def ensure_captures_to_memory_card(camera):
    config = camera.get_config()
    OK, capture_target = gp.gp_widget_get_child_by_name(
        config, "capturetarget")
    if OK >= gp.GP_OK:
        value = gp.check_result(gp.gp_widget_get_value(capture_target))
        if not value in memory_card_choices:
            for i in range(gp.check_result(gp.gp_widget_count_choices(capture_target))):
                choice = gp.check_result(
                    gp.gp_widget_get_choice(capture_target, i))
                if(choice in memory_card_choices):
                    gp.check_result(gp.gp_widget_set_value(
                        capture_target, choice))
                    gp.check_result(gp.gp_camera_set_config(camera, config))
                    print(f'Set capture target to "{choice}".')
                    break


class RaspiRemoteServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_file("/index.htm")
        else:
            self.send_file(self.path)

    def do_POST(self):
        if self.path == "/capture":
            code, message = do_capture()
            self.send_response(code)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes(message, "utf-8"))
        else:
            self.send_response(404)

    def send_file(self, path):
        print("----")
        print(path)
        path = relpath(path, "/")
        print(path)
        path = os.path.join(public_path, path)
        print(path)
        path = os.path.realpath(path)
        print(path)
        print("----")

        if not os.path.exists(path):
            print(f"Failed to find file '{path}'")
            self.send_response(404)
            return

        if not path.startswith(public_path):
            print(f"Attempt to access file outside of public path!: '{path}'")
            self.send_response(404)
            return

        self.send_response(200)
        self.send_header("Content-type", get_mime_type(path))
        self.end_headers()

        file = open(path, "rb")
        self.wfile.write(file.read())
        file.close()


if __name__ == "__main__":
    hostName = "192.168.1.202"
    serverPort = 80
    webServer = HTTPServer((hostName, serverPort), RaspiRemoteServer)
    print("Server started 'http://%s:%s'" % (hostName, serverPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")
