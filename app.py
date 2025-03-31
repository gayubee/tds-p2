import os
import json
import base64
import logging
import re
from flask import Flask, request, jsonify, render_template
from typing import Optional
from utils import (
    process_question,
    download_file_from_url,
    save_upload_file_temp,
    remove_temp_file,
    compress_image_losslessly
)

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
        
        # Handle file input (either URL or uploaded file)
        if file:
            if isinstance(file, str) and file.startswith(('http://', 'https://')):
                temp_file_path = download_file_from_url(file)
                if not temp_file_path:
                    return jsonify({"error": "Failed to download file from URL"}), 400
            elif hasattr(file, 'save'):  # Uploaded file
                temp_file_path = save_upload_file_temp(file)
                if not temp_file_path:
                    return jsonify({"error": "Failed to process uploaded file"}), 400
        
        # Check for image compression request
        if ("compress" in question.lower() or "reduce size" in question.lower()) and \
           "image" in question.lower() and ("lossless" in question.lower() or "identical" in question.lower()):
            
            params = {}
            if temp_file_path:
                params["uploaded_file_path"] = temp_file_path
            else:
                url_match = re.search(r'(https?://\S+)', question)
                if url_match:
                    params["url"] = url_match.group(1)
                else:
                    return jsonify({"error": "No image provided for compression"}), 400
            
            result = compress_image_losslessly(params)
            
            if temp_file_path:
                remove_temp_file(temp_file_path)
            
            if "success" in result and result["success"]:
                file_path = result["file_path"]
                try:
                    if not os.path.exists(file_path):
                        return jsonify({"error": "Compressed file not found"}), 500
                        
                    with open(file_path, "rb") as image_file:
                        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                    
                    os.remove(file_path)
                    
                    return jsonify({"answer": encoded_image})
                except Exception as e:
                    logger.error(f"Error encoding file: {str(e)}")
                    return jsonify({"error": f"Error encoding file: {str(e)}"}), 500
            else:
                return jsonify({"error": result.get("error", "Unknown error during compression")}), 400
        
        # Process other types of requests
        answer = process_question(question, temp_file_path)
        
        if temp_file_path:
            remove_temp_file(temp_file_path)
            
        return jsonify({"answer": answer})
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/", methods=["GET"])
def root():
    return render_template('index.html')

@app.route('/ui', methods=['GET'])
def ui():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
