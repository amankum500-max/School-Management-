from fastapi import FastAPI, File, UploadFile, Form
import face_recognition
import numpy as np
import io

app = FastAPI()

@app.post("/verify-face")
async def verify_face(file: UploadFile = File(...), stored_embedding: str = Form(...)):
    contents = await file.read()
    image = face_recognition.load_image_file(io.BytesIO(contents))
    live_encodings = face_recognition.face_encodings(image)
    
    if not live_encodings:
        return {"status": "FAIL", "message": "No face detected"}
        
    # Database se aaya hua embedding (JSON string to numpy array)
    db_embedding = np.fromstring(stored_embedding, sep=',')
    
    # AI Matching (Tolerance 0.45 for high security)
    matches = face_recognition.compare_faces([db_embedding], live_encodings[0], tolerance=0.45)
    distance = face_recognition.face_distance([db_embedding], live_encodings[0])
    
    if matches[0]:
        return {"status": "SUCCESS", "confidence": f"{(1-distance[0])*100:.2f}%"}
    return {"status": "FAIL", "message": "Identity Mismatch"}
