"""Card detection and perspective correction.

Finds the card's rectangular outline in a photo (which may include some
background, be at a slight angle, etc.) and warps it to a straight,
axis-aligned, portrait-orientation crop so the rest of the pipeline can
assume a clean top-down view of the card.
"""

from typing import Optional

import cv2
import numpy as np

STANDARD_ASPECT = 2.5 / 3.5  # width / height for a standard trading card


def order_points(pts: np.ndarray) -> np.ndarray:
    """Order 4 points as top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1).reshape(-1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _largest_quad(gray: np.ndarray) -> Optional[np.ndarray]:
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 30, 100)
    edges = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=1)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    frame_area = gray.shape[0] * gray.shape[1]
    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < 0.1 * frame_area:
        return None

    peri = cv2.arcLength(largest, True)
    approx = cv2.approxPolyDP(largest, 0.02 * peri, True)
    if len(approx) == 4:
        return approx.reshape(4, 2).astype(np.float32)

    x, y, w, h = cv2.boundingRect(largest)
    return np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], dtype=np.float32)


def detect_card(image: np.ndarray) -> np.ndarray:
    """Return a straightened, portrait-oriented crop of the card found in
    `image`. Falls back to the original image if no clear quadrilateral can
    be found (e.g. the photo is already a tight crop of just the card)."""
    if image is None or image.size == 0:
        raise ValueError("Empty image")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    pts = _largest_quad(gray)
    if pts is None:
        warped = image
    else:
        rect = order_points(pts)
        (tl, tr, br, bl) = rect
        width_a = np.linalg.norm(br - bl)
        width_b = np.linalg.norm(tr - tl)
        max_width = max(int(width_a), int(width_b), 1)

        height_a = np.linalg.norm(tr - br)
        height_b = np.linalg.norm(tl - bl)
        max_height = max(int(height_a), int(height_b), 1)

        dst = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1],
        ], dtype=np.float32)

        matrix = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, matrix, (max_width, max_height))

    h, w = warped.shape[:2]
    if w > h:
        warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)
    return warped


def decode_image(data: bytes) -> np.ndarray:
    array = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode image data")
    return image
