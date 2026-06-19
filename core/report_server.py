"""
Report Server Module
Acts as the presentation layer for the application. 
Generates a static HTML dashboard using Jinja2 and serves it locally 
using Python's built-in HTTP server, completely avoiding the need for 
heavy web frameworks like Flask or Django.
"""
import os
import http.server
import socketserver
from typing import List, Dict, Any
from jinja2 import Environment, FileSystemLoader

def generate_and_serve_report(commits_data: List[Dict[str, Any]]) -> None:
    """
    Renders the evaluated commits into an HTML template, saves it to a public directory,
    and serves it locally on port 3546.
    """
    # Robust Path Resolution:
    # Dynamically resolve absolute paths based on the current file's location.
    # This ensures the script can be executed safely from any working directory or OS.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    templates_dir = os.path.join(project_root, 'templates')
    public_dir = os.path.join(project_root, 'public')
    
    # Ensure the public directory exists before attempting file I/O
    os.makedirs(public_dir, exist_ok=True)
    
    # Phase 1: Templating
    # Initialize Jinja2 environment and load the template
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('report.html')
    
    # Inject the merged commit/review data into the HTML structure
    rendered_html = template.render(commits=commits_data)
    
    # Phase 2: Static Generation
    # Write the output to public/index.html
    output_file_path = os.path.join(public_dir, 'index.html')
    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(rendered_html)
        
    # Phase 3: Local Serving
    port = 3546
    
    # Change the current working directory to public so the simple HTTP 
    # server naturally serves index.html as the root directory default.
    os.chdir(public_dir)
    
    handler = http.server.SimpleHTTPRequestHandler
    
    # Developer Experience (DX) Optimization:
    # Allows the OS to immediately release the port when the server is stopped,
    # preventing frustrating "Address already in use" errors during rapid testing.
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", port), handler) as httpd:
        print("Report generated successfully.")
        print(f"Serving at: http://localhost:{port}")
        print("Press Ctrl+C to stop the server.")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            # Graceful shutdown on user exit
            print("\nShutting down the local server.")
            httpd.server_close()