
import os
import traceback
import sys
import argparse
import json
import utils
import flow_run

import tensorflow as tf

from eyeflow_sdk import edge_client
from eyeflow_sdk.log_obj import CONFIG, log

os.environ["CONF_PATH"] = os.path.dirname(__file__)
# ----------------------------------------------------------------------------------------------------------------------------------


def parse_args(args):
    """ Parse the arguments.
    """
    parser = argparse.ArgumentParser(description='Process a flow.')
    parser.add_argument('--monitor', help='Show image of detection real-time.', action='store_true')
    parser.add_argument('--video', help='Record image of detection in a video.', action='store_true')
    parser.add_argument('--save_split_imgs', help='Path to save split images of detections to a folder.', type=str)
    parser.add_argument('--save_img', help='Save concatenated image of detections to a folder.', type=str)
    parser.add_argument('--serve_image_host', help='Serve image host name.', default="localhost", type=str)
    parser.add_argument('--serve_image_port', help='Serve image host port', type=int)

    return parser.parse_args(args)
# ----------------------------------------------------------------------------------------------------------------------------------

def load_edge_data_json_file(json_path):
    log.info(f'Loading Json: {json_path}')
    with open(json_path, 'r') as json_file:
        return json.load(json_file)
# ----------------------------------------------------------------------------------------------------------------------------------

def save_edge_data_json_file(edge_data, json_path):
    log.info(f'save Json: {json_path}')
    with open(json_path, 'w') as json_file:
        return json.dump(edge_data, json_file)
# ----------------------------------------------------------------------------------------------------------------------------------

def main(args=None):
    # parse arguments
    if args is None:
        args = sys.argv[1:]

    args = parse_args(args)

    os.environ['TF_CUDNN_USE_AUTOTUNE'] = "1"
    # CUDNN_LOGINFO_DBG=1;
    # CUDNN_LOGDEST_DBG=stdout

    physical_devices = tf.config.experimental.list_physical_devices('GPU')
    if len(physical_devices) > 0:
        config = tf.config.experimental.set_memory_growth(physical_devices[0], True)

    app_info, app_token = utils.get_license()
    log.info(f'Edge ID: {app_info["edge_id"]} - System ID: {app_info.get("device_sn")}')
    utils.check_license(app_info)

    try:
        save_split_images = ''
        edge_data = edge_client.get_edge_data(app_token)
        json_path = f'/opt/eyeflow/edge_data.json'
        if not edge_data:
            edge_data = load_edge_data_json_file(json_path)
            if not edge_data:
                raise Exception("Fail getting edge_data")
        else:
            save_edge_data_json_file(edge_data, json_path)

        log.info(edge_data)
        flow_id = edge_data["flow_id"]

        out_monitor_single_image = []
        out_monitor_multiple_images = []

        if args.monitor:
            mon = flow_run.MonitorShow(flow_id)
            out_monitor_single_image.append(mon)

        if args.video:
            vid = flow_run.VideoSave(flow_id)
            out_monitor_single_image.append(vid)

        if args.save_img:
            sav = flow_run.ImageSave(edge_data["flow_name"], args.save_img)
            out_monitor_single_image.append(sav)

        if args.serve_image_host and args.serve_image_port:
            serv = flow_run.ImageServ(flow_id, args.serve_image_host, args.serve_image_port)
            out_monitor_multiple_images.append(serv)

        if args.save_split_imgs:
            save_split_images = flow_run.SaveSplitImage(flow_id, args.serve_image_port)
            out_monitor_multiple_images.append(save_split_images)

        log.info(f"Runnig flow at edge - Flow ID: {flow_id}")

        flow_data = edge_client.get_flow(app_token, flow_id)
        if not flow_data:
            local_cache = os.path.join(CONFIG["flow_folder"], flow_id + '.json')
            flow_data = load_edge_data_json_file(local_cache)

        utils.prepare_models(app_token, flow_data)
        utils.get_flow_components(app_token, flow_data)

        flow_obj = flow_run.FlowRun(flow_id, flow_data, device_info=app_info["edge_id"])
        flow_obj.process_flow(img_output_single=out_monitor_single_image, image_output_multiple=out_monitor_multiple_images, out_frame=(640, 480))

        utils.upload_flow_extracts(app_token, flow_data)

    except Exception as expt:
        log.error(f'Fail processing flow')
        log.error(traceback.format_exc())
        return
# ----------------------------------------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    main()