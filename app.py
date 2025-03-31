import os
import re
import json
import logging
import base64
from flask import Flask, request, jsonify, render_template
from function_mappings import execute_function
from utils import download_file_from_url, save_upload_file_temp, remove_temp_file

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route("/api/", methods=["POST"])
def solve_question():
    try:
        question = request.form.get("question")
        if not question:
            return jsonify({"error": "Question is required"}), 400
        
        file = request.form.get("file") or request.files.get("file")
        temp_file_path = None
        
        # Process file (URL or uploaded)
        if file:
            if isinstance(file, str) and file.startswith(('http://', 'https://')):
                temp_file_path = download_file_from_url(file)
                if not temp_file_path:
                    return jsonify({"error": "Failed to download file from URL"}), 400
            elif hasattr(file, 'save'):  # FileStorage object
                temp_file_path = save_upload_file_temp(file)
                if not temp_file_path:
                    return jsonify({"error": "Failed to process uploaded file"}), 400

        # Pattern Matching for Specific Tasks
        function_name = None
        params = {}

        # Extract URL if present
        url_match = re.search(r'(https?://\S+)', question)
        if url_match:
            params["url"] = url_match.group(1)

        # Assign file path if available
        if temp_file_path:
            params["uploaded_file_path"] = temp_file_path

        # Check for various patterns and determine function to call
        if all(x in question.lower() for x in ["download", "zip", "extract", "rename", "digit", "grep", "sort", "sha256sum", "mv", "a1b9c.txt"]):
            function_name = "process_zip_move_rename_grep"

        elif "write sql" in question.lower() and ("database" in question.lower() or "table" in question.lower()):
            function_name = "generate_sql_query"
            params["question"] = question

        elif ("compress" in question.lower() or "reduce size" in question.lower()) and "image" in question.lower() and ("lossless" in question.lower() or "identical" in question.lower()):
            function_name = "compress_image_losslessly"

        # If a function was identified, execute it
        if function_name:
            result = execute_function(function_name, params)

            # Handle image compression case separately (returning base64-encoded image)
            if function_name == "compress_image_losslessly" and isinstance(result, dict):
                if "error" in result:
                    return jsonify({"error": result["error"]}), 400
                elif "file_path" in result and os.path.exists(result["file_path"]):
                    with open(result["file_path"], "rb") as f:
                        encoded_image = base64.b64encode(f.read()).decode('utf-8')
                    os.remove(result["file_path"])  # Clean up
                    return jsonify({"answer": encoded_image})
                else:
                    return jsonify(result)

            return jsonify({"answer": result})

        return jsonify({"error": "No matching function found"}), 400

    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500
    finally:
        if temp_file_path:
            remove_temp_file(temp_file_path)

@app.route("/", methods=["GET"])
def root():
    return render_template('index.html')

@app.route('/ui', methods=['GET'])
def ui():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
