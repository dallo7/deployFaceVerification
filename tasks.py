from celery import Celery
from deepface import DeepFace
import logging
import os

# Configure Celery
celery = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')


@celery.task
def verify_face_task(filepath1, filepath2):
    """
    The background task that runs the heavy DeepFace verification.
    """
    try:
        # Add debugging information
        logging.info(f"Processing files: {filepath1}, {filepath2}")

        # Check if files exist
        if not os.path.exists(filepath1):
            raise FileNotFoundError(f"Image 1 not found at path: {filepath1}")
        if not os.path.exists(filepath2):
            raise FileNotFoundError(f"Image 2 not found at path: {filepath2}")

        # Check file sizes
        size1 = os.path.getsize(filepath1)
        size2 = os.path.getsize(filepath2)
        logging.info(f"File sizes: {size1} bytes, {size2} bytes")

        if size1 == 0 or size2 == 0:
            raise ValueError("One or both image files are empty")

        my_custom_threshold = 0.5
        model_name = 'ArcFace'
        distance_metrics = 'cosine'

        # Try to verify with DeepFace
        result = DeepFace.verify(

            img1_path=filepath1,
            img2_path=filepath2,
            model_name=model_name,
            distance_metric=distance_metrics,
            enforce_detection=True
        )

        # Extract the calculated distance
        calculated_distance = result['distance']

        # Apply your custom threshold for the decision
        is_verified = calculated_distance <= my_custom_threshold

        print(f"Model: {model_name}, Distance Metric: {distance_metrics}")
        print(f"Calculated Distance: {calculated_distance:.4f}")
        print(f"My Custom Threshold: {my_custom_threshold}")

        if is_verified:
            print("✅ VERIFIED: The faces are the same based on your custom threshold.")
        else:
            print("❌ NOT VERIFIED: The faces are different based on your custom threshold.")

        if result.get("verified"):
            result["message"] = "The two images are of the same person."
        else:
            result["message"] = "The two images are of different people."

        logging.info(f"Verification result: {result}")
        return result

    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        return {"error": f"File not found: {str(e)}"}
    except ValueError as e:
        logging.error(f"DeepFace ValueError: {e}")
        return {"error": f"Image processing error: {str(e)}"}
    except Exception as e:
        logging.exception("An unexpected error occurred during verification!")
        return {"error": f"Unexpected error: {str(e)}"}
    finally:
        try:
            if os.path.exists(filepath1):
                os.remove(filepath1)
            if os.path.exists(filepath2):
                os.remove(filepath2)
        except Exception as cleanup_error:
            logging.warning(f"Failed to clean up files: {cleanup_error}")
