# This script will fix the app.py file structure

import re

# Read the current app.py file
with open('/mnt/c/Source/AIChatBot/app.py', 'r') as f:
    content = f.read()

# Find the main block
main_block_start = content.find("if __name__ == '__main__':")
if main_block_start == -1:
    print("Could not find main block")
    exit(1)

# Find the route definition that's inside the main block
route_pattern = r'@app\.route\("/test-submission"\).*?default_model=DEFAULT_MODEL_NAME\)'
route_match = re.search(route_pattern, content[main_block_start:], re.DOTALL)

if route_match:
    # Extract the route definition
    route_definition = route_match.group(0)
    
    # Remove the route from inside the main block
    content_after_main = content[main_block_start:]
    content_after_main = content_after_main.replace(route_definition, '')
    
    # Reconstruct the content
    content_before_main = content[:main_block_start]
    
    # Add the route definition before the main block
    fixed_content = content_before_main + route_definition + '\n\n' + content_after_main
    
    # Fix the main block content
    fixed_content = fixed_content.replace(
        'print("Ensure GOOGLE_API_KEY is set in a .env file or environment variables.")',
        '''print("Ensure GOOGLE_API_KEY is set in a .env file or environment variables.")
    print(f"Database file: {os.path.abspath(DB_NAME)}")
    print("Enhanced features available at /api/ endpoints")
    # Use debug=True for development, but turn off in production
    # Use host='0.0.0.0' to make it accessible on the network
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)'''
    )
    
    # Remove duplicate lines
    lines_to_remove = [
        '    print(f"Database file: {os.path.abspath(DB_NAME)}")',
        '    print("Enhanced features available at /api/ endpoints")',
        '    # Use debug=True for development, but turn off in production',
        '    # Use host=\'0.0.0.0\' to make it accessible on the network',
        '    socketio.run(app, debug=True, host=\'0.0.0.0\', port=5000)'
    ]
    
    for line in lines_to_remove:
        # Remove duplicate occurrences
        parts = fixed_content.split(line)
        if len(parts) > 2:  # More than one occurrence
            fixed_content = line.join(parts[:2]) + ''.join(parts[2:])
    
    # Write the fixed content
    with open('/mnt/c/Source/AIChatBot/app.py', 'w') as f:
        f.write(fixed_content)
    
    print("Fixed app.py file structure")
else:
    print("Could not find the misplaced route definition")
