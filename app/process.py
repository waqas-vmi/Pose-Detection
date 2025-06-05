import cv2
import mediapipe as mp
import math
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=True,
    model_complexity=2,
    enable_segmentation=False,
    min_detection_confidence=0.7
)

def validate_image_orientation(landmarks):
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]

    # Use X-distance between shoulders for lateral spread
    x_distance = abs(right_shoulder.x - left_shoulder.x)
    
    # Use Z-depth difference to detect turning of the torso
    z_distance = abs(right_shoulder.z - left_shoulder.z)

    # Use visibility to check if both shoulders are clearly visible
    visible = left_shoulder.visibility > 0.5 and right_shoulder.visibility > 0.5

    if x_distance > 0.15 and z_distance < 0.2 and visible:
        return "Front"
    else:
        return "Side"

def check_full_body_landmarks(landmarks):
    # Check if critical landmarks are detected (shoulders, hips, knees)
    required_landmarks = [
        mp_pose.PoseLandmark.LEFT_SHOULDER,
        mp_pose.PoseLandmark.RIGHT_SHOULDER,
        mp_pose.PoseLandmark.LEFT_HIP,
        mp_pose.PoseLandmark.RIGHT_HIP,
        mp_pose.PoseLandmark.LEFT_KNEE,
        mp_pose.PoseLandmark.RIGHT_KNEE
    ]
    
    # If any of the required landmarks are missing, return False
    for lm in required_landmarks:
        if landmarks[lm].visibility < 0.5:
            return False
    return True

def calculate_visual_bmi(declared_weight_kg, visual_height_ratio, shoulder_width_ratio):
    if visual_height_ratio <= 0 or shoulder_width_ratio <= 0:
        return {"error": "Invalid visual measurements."}

    # Use a normalizing factor for height (1.7m as average height)
    visual_height_m = 1.7  # Assume an average human height in meters

    # Visual height is adjusted based on the body ratio
    visual_height_m *= visual_height_ratio
    visual_height_m /= shoulder_width_ratio  # Scale according to shoulder width

    # Calculate the visual BMI using the visual height
    visual_bmi = declared_weight_kg / (visual_height_m ** 2)
    
    return visual_bmi

def calculate_bmi(image_path, declared_height_cm, declared_weight_kg):
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = pose.process(image_rgb)

    if not results.pose_landmarks:
        return {"error": "Pose not detected."}

    landmarks = results.pose_landmarks.landmark

    # Check if it's a full-body pose (not just a face)
    if not check_full_body_landmarks(landmarks):
        return {"error": "Full-body pose required. Missing critical landmarks."}

    orientation = validate_image_orientation(landmarks)

    # Extract key points
    nose = landmarks[mp_pose.PoseLandmark.NOSE]
    heel_left = landmarks[mp_pose.PoseLandmark.LEFT_HEEL]
    heel_right = landmarks[mp_pose.PoseLandmark.RIGHT_HEEL]
    shoulder_left = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    shoulder_right = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]

    # Visual height estimation (head to heel)
    head_to_heel_y = max(heel_left.y, heel_right.y) - landmarks[mp_pose.PoseLandmark.NOSE].y
    visual_height_ratio = abs(head_to_heel_y)

    # Shoulder width (using 3D space for better accuracy)
    shoulder_width = math.sqrt(
        (shoulder_right.x - shoulder_left.x) ** 2 +
        (shoulder_right.y - shoulder_left.y) ** 2 +
        (shoulder_right.z - shoulder_left.z) ** 2
    )

    # Aspect ratio for visual proportion (height-to-width)
    if shoulder_width == 0:
        return {"error": "Invalid pose (shoulder width = 0)"}
    body_ratio = visual_height_ratio / shoulder_width  # taller = bigger ratio

    # Declared BMI calculation
    height_m = declared_height_cm / 100
    declared_bmi = round(declared_weight_kg / (height_m ** 2), 2)

    # BMI matching logic based on declared BMI
    if declared_bmi < 18.5:
        bmi_match = "Underweight"
    elif 18.5 <= declared_bmi <= 24.9:
        bmi_match = "Normal weight"
    elif 25 <= declared_bmi < 29.9:
        bmi_match = "Overweight"
    else:
        bmi_match = "Obesity"

    # Now, let's check if the declared BMI matches the calculated body ratio BMI
    visual_bmi = calculate_visual_bmi(declared_weight_kg, visual_height_ratio, shoulder_width)

    # Difference threshold: We can set a tolerance for acceptable difference
    bmi_difference = abs(visual_bmi - declared_bmi)
    verification_result = "Verification passed"

    if visual_bmi > 3.0:  # Set an acceptable threshold for discrepancy (lowered the threshold)
        verification_result = f"Possible mismatch - BMI discrepancy ({bmi_difference:.2f})"
        logging.warning(f"BMI mismatch detected: {bmi_difference:.2f}")

    response = {
        "declared_bmi": declared_bmi,
        "visual_bmi": visual_bmi,
        "input_height_cm": declared_height_cm,
        "input_weight_kg": declared_weight_kg,
        "visual_height_ratio": round(visual_height_ratio, 3),
        "shoulder_width_ratio": round(shoulder_width, 3),
        "visual_body_ratio": round(body_ratio, 2),
        "orientation": orientation,
        "bmi_category": bmi_match,
        "verification_result": verification_result
    }

    logging.info(f"Response: {response}")

    return response

