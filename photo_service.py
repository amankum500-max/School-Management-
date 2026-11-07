import os
import cloudinary
import cloudinary.uploader

# Cloudinary कॉन्फ़िगरेशन (Render के Environment Variables से)
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

def is_configured():
    """चेक करता है कि Cloudinary सेट है या नहीं"""
    return bool(os.environ.get('CLOUDINARY_CLOUD_NAME'))

def upload_student_photo(student_id, file):
    """फोटो को Cloudinary पर अपलोड करता है और URL लौटाता है"""
    try:
        result = cloudinary.uploader.upload(
            file, 
            folder=f"student_photos/{student_id}", # फोल्डर में सेव होगी
            resource_type="image"
        )
        return {"ok": True, "url": result['secure_url']}
    except Exception as e:
        print(f"Cloudinary Upload Error: {e}")
        return {"ok": False, "error": str(e)}

def upload_student_document(student_id, doc_type, file, doc_name):
    """डॉक्यूमेंट को Cloudinary पर अपलोड करता है"""
    try:
        result = cloudinary.uploader.upload(
            file,
            folder=f"student_documents/{student_id}/{doc_type}",
            resource_type="auto"
        )
        return {
            "ok": True,
            "url": result['secure_url'],
            "size": result.get('bytes', 0),
            "type": result.get('format', 'unknown')
        }
    except Exception as e:
        print(f"Cloudinary Doc Upload Error: {e}")
        return {"ok": False, "error": str(e)}

def delete_student_photo(student_id):
    """डेटाबेस से फोटो हटाने के लिए (फिलहाल True लौटा रहे हैं)"""
    return True
