import qrcode


async def generate_qr_code(
    data: str,
    size: int = 10,
    border: int = 4,
    fill_color: str = "black",
    back_color: str = "white",
):
    """
    Generate a QR code image from the given data.

    Args:
        data: The data to encode in the QR code.
        size: The size of the QR code in pixels.
        border: The border width of the QR code in pixels.
        fill_color: The color of the QR code.
        back_color: The color of the background.

    Returns:
        A QR code image.

    Raises:
        ValueError: If the size or border is not a positive integer.
    """
    if size <= 0:
        raise ValueError("Size must be a positive integer")
    if border < 0:
        raise ValueError("Border must be a non-negative integer")

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color=fill_color, back_color=back_color)
