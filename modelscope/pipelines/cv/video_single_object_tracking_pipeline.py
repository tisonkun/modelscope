import os.path as osp
from typing import Any, Dict

import cv2

from modelscope.metainfo import Pipelines
from modelscope.models.cv.video_single_object_tracking.config.ostrack import \
    cfg
from modelscope.models.cv.video_single_object_tracking.tracker.ostrack import \
    OSTrack
from modelscope.models.cv.video_single_object_tracking.utils.utils import \
    check_box
from modelscope.outputs import OutputKeys
from modelscope.pipelines.base import Input, Pipeline
from modelscope.pipelines.builder import PIPELINES
from modelscope.utils.constant import ModelFile, Tasks
from modelscope.utils.logger import get_logger

logger = get_logger()


@PIPELINES.register_module(
    Tasks.video_single_object_tracking,
    module_name=Pipelines.video_single_object_tracking)
class VideoSingleObjectTrackingPipeline(Pipeline):

    def __init__(self, model: str, **kwargs):
        """
        use `model` to create a single object tracking pipeline
        Args:
            model: model id on modelscope hub.
        """
        super().__init__(model=model, **kwargs)
        self.cfg = cfg
        ckpt_path = osp.join(model, ModelFile.TORCH_MODEL_BIN_FILE)
        logger.info(f'loading model from {ckpt_path}')
        self.tracker = OSTrack(ckpt_path, self.device)
        logger.info('init tracker done')

    def preprocess(self, input) -> Input:
        self.video_path = input[0]
        self.init_bbox = input[1]
        return input

    def forward(self, input: Input) -> Dict[str, Any]:
        output_boxes = []
        cap = cv2.VideoCapture(self.video_path)
        success, frame = cap.read()
        if success is False:
            raise Exception(
                'modelscope error: %s can not be decoded by OpenCV.' %
                (self.video_path))

        init_box = self.init_bbox
        frame_h, frame_w = frame.shape[0:2]
        if not check_box(init_box, frame_h, frame_w):
            raise Exception('modelscope error: init_box out of image range ',
                            init_box)
        output_boxes.append(init_box.copy())
        init_box[2] = init_box[2] - init_box[0]
        init_box[3] = init_box[3] - init_box[1]
        self.tracker.initialize(frame, {'init_bbox': init_box})
        logger.info('init bbox done')

        while True:
            ret, frame = cap.read()
            if frame is None:
                break
            out = self.tracker.track(frame)
            state = [int(s) for s in out['target_bbox']]
            output_boxes.append(state)
        cap.release()
        logger.info('tracking process done')

        return {
            OutputKeys.BOXES: output_boxes,
        }

    def postprocess(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return inputs
