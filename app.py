from flask import Flask, request, jsonify, url_for
from celery.result import AsyncResult
import os
import uuid
from tasks import verify_face_task, celery

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp'}
UPLOAD_FOLDER = 'uploads'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/verify', methods=['POST'])
def upload_and_verify():
    """
    Receives images, saves them, and dispatches the verification task to Celery.
    """

    if 'image1' not in request.files or 'image2' not in request.files:
        return jsonify({"error": "Please upload two images"}), 400
    image1 = request.files['image1']
    image2 = request.files['image2']
    if not (allowed_file(image1.filename) and allowed_file(image2.filename)):
        return jsonify({"error": "Invalid file format"}), 400

    filename1 = str(uuid.uuid4()) + os.path.splitext(image1.filename)[1]
    filename2 = str(uuid.uuid4()) + os.path.splitext(image2.filename)[1]
    filepath1 = os.path.join(app.config['UPLOAD_FOLDER'], filename1)
    filepath2 = os.path.join(app.config['UPLOAD_FOLDER'], filename2)
    image1.save(filepath1)
    image2.save(filepath2)

    # Offload the task to Celery
    task = verify_face_task.delay(filepath1, filepath2)

    # Immediately respond to the client with the task ID
    return jsonify({
        "message": "Verification task has been submitted.",
        "task_id": task.id,
        "result_url": url_for('get_result', task_id=task.id, _external=True)
    }), 202


@app.route('/result/<task_id>')
def get_result(task_id):
    """
    Fetches the result of a background task.
    """
    task = AsyncResult(task_id, app=celery)
    print(task)

    if task.state == 'PENDING':
        response = {'state': task.state, 'status': 'Pending...'}
        print(response)

    elif task.state != 'FAILURE':
        response = {'state': task.state, 'result': task.info}
        print(response)

    else:
        response = {'state': task.state, 'status': str(task.info)}
        print(response)
    return jsonify(response)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5070, debug=False, use_reloader=False)
