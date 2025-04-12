import importlib.resources
import logging
import torch

from transnetv2pt.inference import predict_raw as _predict_raw
from transnetv2pt.inference import predictions_to_scenes

logger = logging.getLogger(__name__) # Use __name__ for logger

# Define custom version of predict_video that accepts a device parameter
def predict_video(filename_or_video, threshold=0.5, probs=False, device=None):
    """
    Wrapper for predict_video that accepts a device parameter.

    Args:
        filename_or_video: Path to video file or numpy array of frames
        threshold: Threshold for scene detection (default: 0.5)
        probs: Whether to include probability values in results (default: False)
        device: PyTorch device to use - either torch.device object or string (default: None,
                which will use CUDA if available, else CPU)
    """
    import ffmpeg
    import numpy as np

    from transnetv2pt.transnetv2_pytorch import TransNetV2

    # Set device if not provided
    if device is None:

        if torch.mps.is_available():
            device = 'mps'
            logger.info('using mps')
        elif torch.cuda.is_available():
            device = torch.device('cuda:0')
            logger.info('using cuda')
        else:
            device = torch.device('cpu')
            logger.info('using cpu')
    elif isinstance(device, str):
        logger.info(device)
        device = torch.device(device)

    # Load the model
    model = TransNetV2()
    # Find weights file relative to installed package
    try:
        with importlib.resources.path('transnetv2pt', 'transnetv2-pytorch-weights.pth') as weights_path:
            model.load_state_dict(torch.load(str(weights_path), map_location=device))
    except FileNotFoundError:
        logger.error("Could not find 'transnetv2-pytorch-weights.pth' within the transnetv2pt package.")
        raise # Re-raise the error

    # Process the video
    if isinstance(filename_or_video, str):
        video_stream, err = ffmpeg.input(filename_or_video).output(
            "pipe:", format="rawvideo", pix_fmt="rgb24", s="48x27"
        ).run(capture_stdout=True, capture_stderr=True)
        video = np.frombuffer(video_stream, np.uint8).reshape([-1, 27, 48, 3])
    else:
        assert filename_or_video.shape[1] == 27 and filename_or_video.shape[2] == 48 and filename_or_video.shape[3] == 3
        video = filename_or_video

    # Use specified device for predictions
    _, single_frame_pred, _ = predict_raw(model, video, device=device)
    scenes = predictions_to_scenes(single_frame_pred, threshold=threshold, probs=probs)
    return scenes

# Version of predict_raw that accepts a device parameter
def predict_raw(model, video, device=None):
    """
    Custom version of predict_raw function that accepts a device parameter

    Args:
        model: The TransNetV2 model
        video: Video frames as numpy array
        device: PyTorch device to use (default: None, uses CUDA if available, else CPU)
    """
    if device is None:
        device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    return _predict_raw(model, video, device=device)

# Export these functions for external use
__all__ = ['predict_video', 'predict_raw', 'predictions_to_scenes'] 