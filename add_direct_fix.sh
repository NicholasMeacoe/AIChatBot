#!/bin/bash

# Add the direct fix script to the HTML file
echo "Adding direct fix script to HTML..."

# Create a temporary file
cat templates/index.html | awk '
/<script src="{{ url_for('\''static'\'', filename='\''js\/fixed-send-message.js'\'') }}"><\/script>/ {
    print $0;
    print "    <script src=\"{{ url_for('\''static'\'', filename='\''js/direct-fix.js'\'') }}\"></script>";
    next;
}
{ print }
' > templates/index.html.new

# Replace the original file
mv templates/index.html.new templates/index.html

echo "Direct fix script added to HTML!"
