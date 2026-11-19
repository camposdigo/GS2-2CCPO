"""Inspectable JSON model export/inference; never unpickle downloaded models."""
import struct


def export(model, feature_names):
    result = {"schemaVersion": 1, "featureNames": feature_names, "target": "delta_volume_7d_pp"}
    if hasattr(model, "named_steps"):
        scaler = model.named_steps["standardscaler"]
        ridge = model.named_steps["ridge"]
        result.update({"kind": "standardized_ridge", "mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist(), "coefficients": ridge.coef_.tolist(), "intercept": float(ridge.intercept_)})
    else:
        result.update({"kind": "random_forest", "trees": []})
        for estimator in model.estimators_:
            tree = estimator.tree_
            result["trees"].append({"feature": tree.feature.tolist(), "threshold": tree.threshold.tolist(), "left": tree.children_left.tolist(), "right": tree.children_right.tolist(), "value": tree.value[:, 0, 0].tolist()})
    return result


def predict_delta(model, x):
    if len(x) != len(model["featureNames"]):
        raise ValueError("Número de features incompatível com o modelo")
    if model["kind"] == "standardized_ridge":
        return model["intercept"] + sum(coef * (value - mean) / scale for coef, value, mean, scale in zip(model["coefficients"], x, model["mean"], model["scale"]))
    if model["kind"] == "random_forest":
        # sklearn's tree predictor compares float32-converted inputs to thresholds.
        x = [struct.unpack("f", struct.pack("f", value))[0] for value in x]
        values = []
        for tree in model["trees"]:
            node = 0
            while tree["left"][node] != -1:
                node = tree["left"][node] if x[tree["feature"][node]] <= tree["threshold"][node] else tree["right"][node]
            values.append(tree["value"][node])
        return sum(values) / len(values)
    raise ValueError("Tipo de modelo desconhecido")
