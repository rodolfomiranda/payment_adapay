from base64 import b64encode
from io import BytesIO
import qrcode


def generate_b64_qr_image(qr_data):
        qr = qrcode.QRCode()
        qr.add_data(qr_data)
        stream = BytesIO()
        qr.make_image().save(stream=stream)
        return b64encode(stream.getvalue()).decode()
