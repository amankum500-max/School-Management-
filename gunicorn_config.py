import gevent.monkey
gevent.monkey.patch_all()

# रेंडर के फ्री टियर के लिए 1 वर्कर सबसे बेस्ट है
workers = 1 

# टाइमआउट 120 सेकंड कर दें ताकि भारी रिक्वेस्ट भी पूरी हो सकें
timeout = 120
