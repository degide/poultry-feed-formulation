/// a Dart library that exports all models used in the app.
library;

double _d(dynamic v) => (v as num).toDouble();
int _i(dynamic v) => (v as num).toInt();

class User {
  User({required this.userId, required this.name, required this.email, required this.role});
  final int userId;
  final String name;
  final String email;
  final String role;

  factory User.fromJson(Map<String, dynamic> j) => User(
        userId: _i(j['user_id']),
        name: j['name'] as String,
        email: j['email'] as String,
        role: j['role'] as String,
      );
}

class Ingredient {
  Ingredient({required this.id, required this.name, required this.category, required this.isActive});
  final int id;
  final String name;
  final String category;
  final bool isActive;

  factory Ingredient.fromJson(Map<String, dynamic> j) => Ingredient(
        id: _i(j['ingredient_id']),
        name: j['name'] as String,
        category: j['category'] as String,
        isActive: (j['is_active'] as bool?) ?? true,
      );
}

class MarketPrice {
  MarketPrice({
    required this.priceId,
    required this.ingredientId,
    required this.pricePerKg,
    required this.priceDate,
    required this.marketLocation,
  });
  final int priceId;
  final int ingredientId;
  final double pricePerKg;
  final String priceDate;
  final String marketLocation;

  factory MarketPrice.fromJson(Map<String, dynamic> j) => MarketPrice(
        priceId: _i(j['price_id']),
        ingredientId: _i(j['ingredient_id']),
        pricePerKg: _d(j['price_per_kg_rwf']),
        priceDate: j['price_date'] as String,
        marketLocation: j['market_location'] as String,
      );
}

class Flock {
  Flock({
    required this.id,
    required this.name,
    required this.type,
    required this.ageWeeks,
    required this.size,
    this.previousFormulationId,
  });
  final int id;
  final String name;
  final String type; // broiler | layer
  final int ageWeeks;
  final int size;
  final int? previousFormulationId;

  factory Flock.fromJson(Map<String, dynamic> j) => Flock(
        id: _i(j['flock_id']),
        name: j['name'] as String,
        type: j['type'] as String,
        ageWeeks: _i(j['current_age_weeks']),
        size: _i(j['flock_size']),
        previousFormulationId: j['previous_formulation_id'] == null
            ? null
            : _i(j['previous_formulation_id']),
      );
}

class ForecastPoint {
  ForecastPoint({required this.date, required this.price, required this.lower, required this.upper});
  final String date;
  final double price;
  final double lower;
  final double upper;

  factory ForecastPoint.fromJson(Map<String, dynamic> j) => ForecastPoint(
        date: j['date'] as String,
        price: _d(j['price']),
        lower: _d(j['lower']),
        upper: _d(j['upper']),
      );
}

class IngredientForecast {
  IngredientForecast({
    required this.ingredientId,
    required this.ingredientName,
    required this.model,
    required this.history,
    required this.forecast,
  });
  final int ingredientId;
  final String ingredientName;
  final String model;
  final List<ForecastPoint> history;
  final List<ForecastPoint> forecast;

  factory IngredientForecast.fromJson(Map<String, dynamic> j) => IngredientForecast(
        ingredientId: _i(j['ingredient_id']),
        ingredientName: j['ingredient_name'] as String,
        model: j['model'] as String,
        history: ((j['history'] as List?) ?? [])
            .map((e) => ForecastPoint.fromJson(e as Map<String, dynamic>))
            .toList(),
        forecast: ((j['forecast'] as List?) ?? [])
            .map((e) => ForecastPoint.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class MethodMetrics {
  MethodMetrics({required this.method, required this.n, required this.mae, required this.rmse, required this.mape});
  final String method;
  final int n;
  final double mae;
  final double rmse;
  final double mape;

  factory MethodMetrics.fromJson(Map<String, dynamic> j) => MethodMetrics(
        method: j['method'] as String,
        n: _i(j['n']),
        mae: _d(j['mae']),
        rmse: _d(j['rmse']),
        mape: _d(j['mape']),
      );
}

class BacktestResult {
  BacktestResult({required this.testMonths, required this.methods, this.note});
  final int testMonths;
  final List<MethodMetrics> methods;
  final String? note;

  factory BacktestResult.fromJson(Map<String, dynamic> j) => BacktestResult(
        testMonths: _i(j['test_months']),
        methods: ((j['methods'] as List?) ?? [])
            .map((e) => MethodMetrics.fromJson(e as Map<String, dynamic>))
            .toList(),
        note: j['note'] as String?,
      );
}

class ParetoPoint {
  ParetoPoint({
    required this.formulationId,
    required this.cost,
    required this.dtsi,
    required this.cosineDistance,
    required this.generatedBy,
    required this.proportions,
  });
  final int formulationId;
  final double cost;
  final double dtsi;
  final double cosineDistance;
  final String generatedBy; // "NSGA-II" | "LP"
  final Map<String, double> proportions;

  factory ParetoPoint.fromJson(Map<String, dynamic> j) => ParetoPoint(
        formulationId: _i(j['formulation_id']),
        cost: _d(j['total_cost_per_kg_rwf']),
        dtsi: _d(j['dtsi_score']),
        cosineDistance: _d(j['cosine_distance']),
        generatedBy: j['generated_by'] as String,
        proportions: ((j['proportions'] as Map?) ?? {})
            .map((k, v) => MapEntry(k as String, _d(v))),
      );
}

class JobResult {
  JobResult({
    required this.jobId,
    required this.flockId,
    required this.state,
    this.error,
    required this.nsga2Front,
    this.lpSolution,
  });
  final String jobId;
  final int flockId;
  final String state; // pending | running | complete | failed
  final String? error;
  final List<ParetoPoint> nsga2Front;
  final ParetoPoint? lpSolution;

  bool get isDone => state == 'complete' || state == 'failed';

  factory JobResult.fromJson(Map<String, dynamic> j) => JobResult(
        jobId: j['job_id'] as String,
        flockId: _i(j['flock_id']),
        state: j['state'] as String,
        error: j['error'] as String?,
        nsga2Front: ((j['nsga2_front'] as List?) ?? [])
            .map((e) => ParetoPoint.fromJson(e as Map<String, dynamic>))
            .toList(),
        lpSolution: j['lp_solution'] == null
            ? null
            : ParetoPoint.fromJson(j['lp_solution'] as Map<String, dynamic>),
      );
}

class FormulationSummary {
  FormulationSummary({
    required this.id,
    required this.cost,
    required this.dtsi,
    required this.isSelected,
    required this.generatedBy,
    required this.createdAt,
  });
  final int id;
  final double cost;
  final double dtsi;
  final bool isSelected;
  final String generatedBy;
  final String createdAt;

  factory FormulationSummary.fromJson(Map<String, dynamic> j) => FormulationSummary(
        id: _i(j['formulation_id']),
        cost: _d(j['total_cost_per_kg_rwf']),
        dtsi: _d(j['dtsi_score']),
        isSelected: j['is_selected'] as bool,
        generatedBy: j['generated_by'] as String,
        createdAt: j['created_at'] as String,
      );
}

class FormulationIngredient {
  FormulationIngredient({required this.name, required this.percent});
  final String name;
  final double percent;
}

class FormulationDetail {
  FormulationDetail({
    required this.id,
    required this.flockId,
    required this.generatedBy,
    required this.cost,
    required this.dtsi,
    this.cosineDistance,
    required this.isSelected,
    required this.createdAt,
    required this.ingredients,
  });
  final int id;
  final int flockId;
  final String generatedBy;
  final double cost;
  final double dtsi;
  final double? cosineDistance;
  final bool isSelected;
  final String createdAt;
  final List<FormulationIngredient> ingredients;

  factory FormulationDetail.fromJson(Map<String, dynamic> j) => FormulationDetail(
        id: _i(j['formulation_id']),
        flockId: _i(j['flock_id']),
        generatedBy: j['generated_by'] as String,
        cost: _d(j['total_cost_per_kg_rwf']),
        dtsi: _d(j['dtsi_score']),
        cosineDistance:
            j['cosine_distance'] == null ? null : _d(j['cosine_distance']),
        isSelected: j['is_selected'] as bool,
        createdAt: j['created_at'] as String,
        ingredients: ((j['ingredients'] as List?) ?? [])
            .map((e) => FormulationIngredient(
                  name: (e as Map<String, dynamic>)['ingredient_name'] as String,
                  percent: _d(e['proportion_percent']),
                ))
            .toList(),
      );
}
