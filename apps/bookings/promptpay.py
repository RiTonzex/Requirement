import urllib.parse
import qrcode
import qrcode.image.svg


def crc16_ccitt(data: str) -> str:
    """คำนวณ CRC16-CCITT (polynomial 0x1021, init 0xFFFF) ตามมาตรฐาน EMVCo"""
    crc = 0xFFFF
    for ch in data:
        crc ^= (ord(ch) << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def generate_promptpay_payload(target: str, amount: float = None) -> str:
    """
    สร้างข้อความ EMVCo PromptPay QR Payload มาตรฐานธนาคารแห่งประเทศไทย
    :param target: เบอร์โทรศัพท์มือถือ (10 หลัก เช่น 0812345678) หรือ เลขบัตรประชาชน (13 หลัก)
    :param amount: จำนวนเงิน (บาท) ทศนิยม 2 ตำแหน่ง
    """
    clean_target = "".join(filter(str.isdigit, str(target)))
    
    # 00: Payload Format Indicator
    payload = "000201"
    # 01: Point of Initiation Method (12 = Dynamic QR มีระบุจำนวนเงิน, 11 = Static QR)
    payload += "010212" if (amount is not None and amount > 0) else "010211"

    # 29: Merchant Account Information - PromptPay
    # AID: 0016A000000677010111
    aid = "0016A000000677010111"
    
    if len(clean_target) == 13:
        # National ID / Tax ID
        sub_tag = f"0213{clean_target}"
    else:
        # Mobile Phone (0066 + 9 หลักหลัง)
        if clean_target.startswith("0"):
            clean_target = clean_target[1:]
        phone_emv = f"0066{clean_target}".rjust(13, "0")
        sub_tag = f"0113{phone_emv}"
        
    tag29_value = aid + sub_tag
    payload += f"29{len(tag29_value):02d}{tag29_value}"

    # 53: Transaction Currency (764 = THB)
    payload += "5303764"

    # 54: Transaction Amount (ถ้ามี)
    if amount is not None and amount > 0:
        formatted_amount = f"{float(amount):.2f}"
        payload += f"54{len(formatted_amount):02d}{formatted_amount}"

    # 58: Country Code (TH)
    payload += "5802TH"

    # 63: CRC16 Checksum
    crc_prefix = "6304"
    crc = crc16_ccitt(payload + crc_prefix)
    return payload + crc_prefix + crc


def generate_promptpay_qr_svg(target: str, amount: float = None) -> str:
    """
    สร้าง SVG Data URI ของ PromptPay QR Code เพื่อแสดงผลในแท็ก <img> ได้ทันที
    """
    payload = generate_promptpay_payload(target, amount)
    factory = qrcode.image.svg.SvgPathImage
    qr_img = qrcode.make(payload, image_factory=factory, box_size=10, border=1)
    svg_data = qr_img.to_string().decode('utf-8')
    
    encoded_svg = urllib.parse.quote(svg_data)
    return f"data:image/svg+xml;utf8,{encoded_svg}"
