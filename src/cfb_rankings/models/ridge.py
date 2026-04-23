from __future__ import annotations

from collections.abc import Sequence

try:
    import numpy as _np
except Exception:  # pragma: no cover - local fallback path
    _np = None


def fit_ridge_with_prior(
    design_matrix: Sequence[Sequence[float]],
    target: Sequence[float],
    weights: Sequence[float],
    alpha_prior: float,
    prior_mean: Sequence[float],
    alpha_ridge: float = 1.0,
) -> list[float]:
    if _numpy_ready():
        design = _np.asarray(design_matrix, dtype=float)
        target_array = _np.asarray(target, dtype=float)
        weight_array = _np.asarray(weights, dtype=float)
        prior_array = _np.asarray(prior_mean, dtype=float)
        if design.size == 0:
            return prior_array.tolist()

        sqrt_weights = _np.sqrt(weight_array).reshape(-1, 1)
        weighted_design = design * sqrt_weights
        weighted_target = target_array * _np.sqrt(weight_array)

        num_features = design.shape[1]
        regularizer = (alpha_prior + alpha_ridge) * _np.eye(num_features)
        lhs = weighted_design.T @ weighted_design + regularizer
        rhs = weighted_design.T @ weighted_target + alpha_prior * prior_array
        return _np.linalg.solve(lhs, rhs).tolist()

    if not design_matrix:
        return [float(value) for value in prior_mean]

    num_features = len(design_matrix[0]) if design_matrix[0] else 0
    if num_features == 0:
        return [float(value) for value in prior_mean]

    rows: list[tuple[tuple[int, ...], tuple[float, ...]]] = []
    for feature_values in design_matrix:
        nonzero_indices: list[int] = []
        nonzero_values: list[float] = []
        for index, value in enumerate(feature_values):
            numeric = float(value)
            if numeric == 0.0:
                continue
            nonzero_indices.append(index)
            nonzero_values.append(numeric)
        rows.append((tuple(nonzero_indices), tuple(nonzero_values)))

    return fit_sparse_ridge_with_prior(
        num_features=num_features,
        rows=rows,
        target=target,
        weights=weights,
        alpha_prior=alpha_prior,
        prior_mean=prior_mean,
        alpha_ridge=alpha_ridge,
    )


def fit_sparse_ridge_with_prior(
    *,
    num_features: int,
    rows: Sequence[tuple[Sequence[int], Sequence[float]]],
    target: Sequence[float],
    weights: Sequence[float],
    alpha_prior: float,
    prior_mean: Sequence[float],
    alpha_ridge: float = 1.0,
) -> list[float]:
    if _numpy_ready():
        prior_array = _np.asarray(prior_mean, dtype=float)
        if not rows:
            return prior_array.tolist()

        lhs = (alpha_prior + alpha_ridge) * _np.eye(num_features, dtype=float)
        rhs = alpha_prior * prior_array.astype(float, copy=True)
        target_array = _np.asarray(target, dtype=float)
        weight_array = _np.asarray(weights, dtype=float)

        for (feature_indices, feature_values), observed_target, row_weight in zip(rows, target_array, weight_array, strict=True):
            if row_weight <= 0:
                continue

            indices = _np.asarray(feature_indices, dtype=int)
            values = _np.asarray(feature_values, dtype=float)
            if indices.size == 0:
                continue

            rhs[indices] += row_weight * values * observed_target
            lhs[_np.ix_(indices, indices)] += row_weight * _np.outer(values, values)

        return _np.linalg.solve(lhs, rhs).tolist()

    prior_vector = [float(value) for value in prior_mean]
    if not rows:
        return prior_vector.copy()

    diagonal = float(alpha_prior + alpha_ridge)
    rhs = [alpha_prior * value for value in prior_vector]
    target_values = [float(value) for value in target]
    weight_values = [float(value) for value in weights]
    normalized_rows: list[tuple[list[int], list[float], float]] = []

    for (feature_indices, feature_values), observed_target, row_weight in zip(rows, target_values, weight_values, strict=True):
        if row_weight <= 0:
            continue

        indices = [int(index) for index in feature_indices]
        values = [float(value) for value in feature_values]
        if not indices:
            continue

        normalized_rows.append((indices, values, row_weight))
        for index, value in zip(indices, values, strict=True):
            rhs[index] += row_weight * value * observed_target

    return _solve_sparse_normal_system(
        num_features=num_features,
        diagonal=diagonal,
        rows=normalized_rows,
        rhs=rhs,
        initial=prior_vector,
    )


def _identity_matrix(size: int, diagonal_value: float) -> list[list[float]]:
    matrix = [[0.0 for _ in range(size)] for _ in range(size)]
    for index in range(size):
        matrix[index][index] = float(diagonal_value)
    return matrix


def _solve_linear_system(lhs: Sequence[Sequence[float]], rhs: Sequence[float]) -> list[float]:
    size = len(lhs)
    if size == 0:
        return []

    matrix = [[float(value) for value in row] for row in lhs]
    vector = [float(value) for value in rhs]

    for pivot_index in range(size):
        pivot_row = max(range(pivot_index, size), key=lambda row_index: abs(matrix[row_index][pivot_index]))
        pivot_value = matrix[pivot_row][pivot_index]
        if abs(pivot_value) < 1e-12:
            raise RuntimeError("Ridge solver encountered a singular matrix.")

        if pivot_row != pivot_index:
            matrix[pivot_index], matrix[pivot_row] = matrix[pivot_row], matrix[pivot_index]
            vector[pivot_index], vector[pivot_row] = vector[pivot_row], vector[pivot_index]

        pivot_value = matrix[pivot_index][pivot_index]
        inverse_pivot = 1.0 / pivot_value
        matrix[pivot_index] = [value * inverse_pivot for value in matrix[pivot_index]]
        vector[pivot_index] *= inverse_pivot

        for row_index in range(size):
            if row_index == pivot_index:
                continue
            factor = matrix[row_index][pivot_index]
            if abs(factor) < 1e-12:
                continue
            matrix[row_index] = [
                row_value - factor * pivot_row_value
                for row_value, pivot_row_value in zip(matrix[row_index], matrix[pivot_index], strict=True)
            ]
            vector[row_index] -= factor * vector[pivot_index]

    return vector


def _numpy_ready() -> bool:
    return _np is not None and hasattr(_np, "eye") and hasattr(_np, "linalg") and hasattr(_np, "asarray")


def _solve_sparse_normal_system(
    *,
    num_features: int,
    diagonal: float,
    rows: Sequence[tuple[Sequence[int], Sequence[float], float]],
    rhs: Sequence[float],
    initial: Sequence[float],
    tolerance: float = 1e-7,
    max_iterations: int | None = None,
) -> list[float]:
    if num_features == 0:
        return []

    if max_iterations is None:
        max_iterations = max(40, min(400, num_features // 2))

    x = [float(value) for value in initial]
    b = [float(value) for value in rhs]
    residual = [b_i - ax_i for b_i, ax_i in zip(b, _sparse_matvec(x, diagonal, rows), strict=True)]
    direction = residual.copy()
    residual_dot = _dot(residual, residual)

    if residual_dot <= tolerance * tolerance:
        return x

    for _iteration in range(max_iterations):
        ad = _sparse_matvec(direction, diagonal, rows)
        denom = _dot(direction, ad)
        if abs(denom) < 1e-12:
            break

        alpha = residual_dot / denom
        x = [x_i + alpha * d_i for x_i, d_i in zip(x, direction, strict=True)]
        residual = [r_i - alpha * ad_i for r_i, ad_i in zip(residual, ad, strict=True)]
        next_residual_dot = _dot(residual, residual)
        if next_residual_dot <= tolerance * tolerance:
            break

        beta = next_residual_dot / residual_dot if residual_dot > 0 else 0.0
        direction = [r_i + beta * d_i for r_i, d_i in zip(residual, direction, strict=True)]
        residual_dot = next_residual_dot

    return x


def _sparse_matvec(
    vector: Sequence[float],
    diagonal: float,
    rows: Sequence[tuple[Sequence[int], Sequence[float], float]],
) -> list[float]:
    result = [diagonal * float(value) for value in vector]
    for indices, values, row_weight in rows:
        dot_product = 0.0
        for index, value in zip(indices, values, strict=True):
            dot_product += float(value) * float(vector[index])
        if dot_product == 0.0:
            continue
        scaled = row_weight * dot_product
        for index, value in zip(indices, values, strict=True):
            result[index] += scaled * float(value)
    return result


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(float(a) * float(b) for a, b in zip(left, right, strict=True))
