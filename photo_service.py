import os
import cloudinary
import cloudinary.uploader

# Cloudinary को सीधे URL से कॉन्फ़िगर करें
# यह Render के Environment Variables से अपने आप उठा लेगा
cloudinary.config(cloudinary_url=os.environ.get('CLOUDINARY_URL'))

def is_configured():
    return bool(os.environ.get('CLOUDINARY_URL'))

def upload_student_photo(student_id, file):
    try:
        # फोटो को Cloudinary पर अपलोड करें
        result = cloudinary.uploader.upload(
            file, 
            folder=f"student_photos/{student_id}"
        )
        return {"ok": True, "url": result['secure_url']}
    except Exception as e:
        print(f"Cloudinary Upload Error: {e}")
        return {"ok": False, "error": str(e)}

def upload_student_document(student_id, doc_type, file, doc_name):
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
    return True
