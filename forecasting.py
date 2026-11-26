
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

def make_features(dates, start_date):
    dates = pd.DatetimeIndex(dates)
    elapsed = (dates - start_date).days.astype(float)
    weekday = dates.dayofweek.to_numpy()
    month = dates.month.to_numpy()
    day_of_year = dates.dayofyear.to_numpy()

    return pd.DataFrame({
        "trend": elapsed,
        "weekday": weekday,
        "month": month,
        "day_of_year": day_of_year,
        "weekday_sin": np.sin(2 * np.pi * weekday / 7),
        "weekday_cos": np.cos(2 * np.pi * weekday / 7),
        "year_sin": np.sin(2 * np.pi * day_of_year / 365.25),
        "year_cos": np.cos(2 * np.pi * day_of_year / 365.25)
    })

def create_models():
    return {
        "线性回归": LinearRegression(),
        "随机森林": RandomForestRegressor(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1
        )
    }

def build_rolling_origins(data_length, forecast_days):
    minimum_train_days = 180
    latest_origin = data_length - forecast_days

    if latest_origin < minimum_train_days:
        return []

    first_origin = max(
        minimum_train_days,
        latest_origin - 360
    )

    origins = list(
        range(first_origin, latest_origin + 1, forecast_days)
    )

    if not origins or origins[-1] != latest_origin:
        origins.append(latest_origin)

    return sorted(set(origins))

def run_rolling_backtest(daily, forecast_days):
    start_date = daily.index.min()
    origins = build_rolling_origins(
        len(daily),
        forecast_days
    )

    if len(origins) < 4:
        raise ValueError(
            "历史数据不足以完成至少 4 轮滚动回测，请扩大日期范围或增加历史数据。"
        )

    model_residuals = {
        "线性回归": [],
        "随机森林": []
    }

    model_absolute_errors = {
        "线性回归": [],
        "随机森林": []
    }

    model_squared_errors = {
        "线性回归": [],
        "随机森林": []
    }

    model_cumulative_errors = {
        "线性回归": [],
        "随机森林": []
    }

    window_details = []

    for origin in origins:
        train = daily.iloc[:origin]
        test = daily.iloc[origin:origin + forecast_days]

        if len(test) != forecast_days:
            continue

        x_train = make_features(train.index, start_date)
        x_test = make_features(test.index, start_date)

        y_train = train.to_numpy(dtype=float)
        y_test = test.to_numpy(dtype=float)

        window_result = {
            "预测起点": test.index.min(),
            "预测结束": test.index.max(),
            "实际累计销售额": float(y_test.sum())
        }

        for name, model in create_models().items():
            model.fit(x_train, y_train)

            predictions = np.maximum(
                model.predict(x_test),
                0
            )

            residuals = y_test - predictions

            model_residuals[name].extend(
                residuals.tolist()
            )

            model_absolute_errors[name].extend(
                np.abs(residuals).tolist()
            )

            model_squared_errors[name].extend(
                np.square(residuals).tolist()
            )

            cumulative_error = float(
                y_test.sum() - predictions.sum()
            )

            model_cumulative_errors[name].append(
                cumulative_error
            )

            window_result[f"{name}预测累计销售额"] = float(
                predictions.sum()
            )

            window_result[f"{name}累计误差"] = cumulative_error

        window_details.append(window_result)

    if len(window_details) < 4:
        raise ValueError("有效滚动回测窗口不足，无法可靠评估模型。")

    comparison = {}

    for name in model_residuals:
        absolute_errors = np.asarray(
            model_absolute_errors[name],
            dtype=float
        )

        squared_errors = np.asarray(
            model_squared_errors[name],
            dtype=float
        )

        comparison[name] = {
            "mae": float(absolute_errors.mean()),
            "rmse": float(np.sqrt(squared_errors.mean()))
        }

    selected_name = min(
        comparison,
        key=lambda name: comparison[name]["mae"]
    )

    selected_residuals = np.asarray(
        model_residuals[selected_name],
        dtype=float
    )

    selected_cumulative_errors = np.asarray(
        model_cumulative_errors[selected_name],
        dtype=float
    )

    return {
        "origins": origins,
        "comparison": comparison,
        "selected_model": selected_name,
        "residuals": selected_residuals,
        "cumulative_errors": selected_cumulative_errors,
        "window_details": pd.DataFrame(window_details)
    }

def forecast_sales(df, days=30):
    data = df.copy()

    data["order_date"] = pd.to_datetime(
        data["order_date"],
        errors="coerce"
    )

    data["revenue"] = pd.to_numeric(
        data["revenue"],
        errors="coerce"
    )

    data = data.dropna(
        subset=["order_date", "revenue"]
    )

    if data.empty:
        raise ValueError("没有足够的历史销售数据用于预测。")

    daily = (
        data.groupby(data["order_date"].dt.normalize())["revenue"]
        .sum()
        .sort_index()
    )

    full_dates = pd.date_range(
        start=daily.index.min(),
        end=daily.index.max(),
        freq="D"
    )

    daily = daily.reindex(
        full_dates,
        fill_value=0
    )

    daily.index.name = "日期"

    if len(daily) < 210:
        raise ValueError(
            "至少需要 210 天历史数据才能完成滚动 30 天回测。"
        )

    backtest = run_rolling_backtest(
        daily,
        days
    )

    selected_name = backtest["selected_model"]
    residuals = backtest["residuals"]
    cumulative_errors = backtest["cumulative_errors"]

    daily_lower_error = float(
        np.quantile(residuals, 0.10)
    )

    daily_upper_error = float(
        np.quantile(residuals, 0.90)
    )

    final_features = make_features(
        daily.index,
        daily.index.min()
    )

    final_model = create_models()[selected_name]

    final_model.fit(
        final_features,
        daily.to_numpy(dtype=float)
    )

    future_dates = pd.date_range(
        start=daily.index.max() + pd.Timedelta(days=1),
        periods=days,
        freq="D"
    )

    future_features = make_features(
        future_dates,
        daily.index.min()
    )

    predictions = np.maximum(
        final_model.predict(future_features),
        0
    )

    daily_lower = np.maximum(
        predictions + daily_lower_error,
        0
    )

    daily_upper = np.maximum(
        predictions + daily_upper_error,
        daily_lower
    )

    forecast = pd.DataFrame({
        "日期": future_dates,
        "销售额": predictions,
        "预测下限": daily_lower,
        "预测上限": daily_upper,
        "类型": "预测销售"
    })

    history = pd.DataFrame({
        "日期": daily.index,
        "销售额": daily.values,
        "类型": "历史销售"
    })

    history["7日移动平均"] = (
        history["销售额"].rolling(
            window=7,
            min_periods=1
        ).mean()
    )

    combined = pd.concat(
        [history, forecast],
        ignore_index=True
    )

    forecast_total = float(
        forecast["销售额"].sum()
    )

    cumulative_lower_error = float(
        np.quantile(cumulative_errors, 0.10)
    )

    cumulative_upper_error = float(
        np.quantile(cumulative_errors, 0.90)
    )

    cumulative_lower = max(
        0,
        forecast_total + cumulative_lower_error
    )

    cumulative_upper = max(
        cumulative_lower,
        forecast_total + cumulative_upper_error
    )

    comparison = backtest["comparison"]
    selected_metrics = comparison[selected_name]

    metrics = {
        "selected_model": selected_name,
        "mae": selected_metrics["mae"],
        "rmse": selected_metrics["rmse"],
        "test_days": len(backtest["origins"]) * days,
        "backtest_windows": len(backtest["window_details"]),
        "comparison": comparison,
        "daily_lower_error": daily_lower_error,
        "daily_upper_error": daily_upper_error,
        "cumulative_lower": cumulative_lower,
        "cumulative_upper": cumulative_upper,
        "cumulative_interval_available": len(cumulative_errors) >= 4,
        "block_sample_count": len(cumulative_errors),
        "window_details": backtest["window_details"]
    }

    return combined, forecast, metrics
