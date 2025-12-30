import http.server
import socketserver
import json
import os
from datetime import datetime

PORT = 8081
DATA_FILE = "reservations.json"

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/reservations':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            data = []
            if os.path.exists(DATA_FILE):
                try:
                    with open(DATA_FILE, 'r') as f:
                        data = json.load(f)
                except json.JSONDecodeError:
                    data = []
            
            self.wfile.write(json.dumps(data).encode())
        else:
            # Serve static files as usual
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/reserve':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                new_entry = json.loads(post_data.decode())
                
                # Load existing data
                data = []
                if os.path.exists(DATA_FILE):
                    try:
                        with open(DATA_FILE, 'r') as f:
                            data = json.load(f)
                    except json.JSONDecodeError:
                        data = [] # partial file or error
                
                # Append new entry
                data.append(new_entry)
                
                # Save back to file
                with open(DATA_FILE, 'w') as f:
                    json.dump(data, f, indent=2)
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Reservation saved"}).encode())
                
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_response(404)
            self.end_headers()

print(f"Starting server on http://localhost:{PORT}")
print(f"Saving data to {os.path.abspath(DATA_FILE)}")

# Prepare the data file if it doesn't exist
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

class ThreadingSimpleServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

with ThreadingSimpleServer(("", PORT), CustomHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
