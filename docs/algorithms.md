# Algorithm configuration and limitations

## Vehicle detection and tracking

The detector loads the local model path from `ITS_MODEL_PATH`, filters the standard COCO vehicle class IDs for car, motorcycle, bus, and truck, and returns boxes/confidence/class IDs. `VehicleTracker` calls Ultralytics `model.track(..., persist=True, tracker="bytetrack.yaml")` to retain IDs across frames. No model file is included and no weights are downloaded automatically.

## Lane polygons

Set `ITS_LANE_CONFIG` to a JSON file with lane polygons in source-video pixel coordinates:

```json
{
  "lanes": [
    {"id": "lane_a", "polygon": [[10, 100], [200, 100], [230, 700], [0, 700]]},
    {"id": "lane_b", "polygon": [[205, 100], [400, 100], [450, 700], [230, 700]]}
  ],
  "forbidden_transitions": [["lane_a", "lane_b"]]
}
```

These coordinates are an illustrative schema only; they are not valid calibration for any particular camera. Configure polygons from the actual camera view. The representative point is the bottom-center of each vehicle box. Overlapping polygons are resolved by the first matching lane in the JSON list.

## Rule checking

Only listed lane transitions are considered forbidden. A violation is reported once per tracker ID and transition after the destination lane persists for `ITS_VIOLATION_CONFIRM_FRAMES` observations (default 8). Temporary lane-change behavior that does not match a configured forbidden transition is not a violation. This starter rule is not a substitute for validating road markings, perspective, occlusion, direction, or local traffic regulations.

With no lane configuration, the pipeline can still produce an annotated detection/tracking video but marks its scope as `detection_only` and reports that wrong-lane behavior was not evaluated.
