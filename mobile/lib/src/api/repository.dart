import 'api_client.dart';
import '../models/models.dart';

/// All backend calls the app makes, returning typed models.
class Repository {
  Repository(this.client);
  final ApiClient client;

  // auth
  Future<String> login(String email, String password) async {
    final data = await client.postForm('/auth/login',
        {'username': email, 'password': password});
    return data['access_token'] as String;
  }

  Future<void> registerUser(
          String name, String email, String role, String password) =>
      client.postJson('/auth/register',
          {'name': name, 'email': email, 'role': role, 'password': password});

  Future<User> me() async =>
      User.fromJson(await client.get('/auth/me') as Map<String, dynamic>);

  // ingredients
  Future<List<Ingredient>> ingredients() async {
    final list = await client.get('/ingredients') as List;
    return list.map((e) => Ingredient.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<String>> locations() async {
    final list = await client.get('/market-prices/locations') as List;
    return list.map((e) => e as String).toList();
  }

  Future<List<MarketPrice>> latestPrices(String location) async {
    final list = await client
        .get('/market-prices/latest', query: {'market_location': location}) as List;
    return list.map((e) => MarketPrice.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> addPrice({
    required int ingredientId,
    required double price,
    required String date,
    required String location,
  }) =>
      client.postJson('/market-prices', {
        'ingredient_id': ingredientId,
        'price_per_kg_rwf': price,
        'price_date': date,
        'market_location': location,
      });

  // flocks
  Future<List<Flock>> flocks() async {
    final list = await client.get('/flocks') as List;
    return list.map((e) => Flock.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Flock> createFlock({
    required String name,
    required String type,
    required int ageWeeks,
    required int size,
  }) async =>
      Flock.fromJson(await client.postJson('/flocks', {
        'name': name,
        'type': type,
        'current_age_weeks': ageWeeks,
        'flock_size': size,
      }) as Map<String, dynamic>);

  // forecasts
  Future<List<IngredientForecast>> forecasts({String marketLocation = 'Rwanda'}) async {
    final list = await client.get('/forecasts', query: {'market_location': marketLocation}) as List;
    return list
        .map((e) => IngredientForecast.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<int> refreshForecasts({String marketLocation = 'Rwanda', int horizon = 1}) async {
    final data = await client
        .postJson('/forecasts/refresh?market_location=$marketLocation&horizon_months=$horizon', {}) as Map<String, dynamic>;
    return (data['ingredients_forecast'] as num).toInt();
  }

  Future<BacktestResult> backtest({String marketLocation = 'Rwanda', int testMonths = 6}) async =>
      BacktestResult.fromJson(await client
          .get('/forecasts/backtest', query: {'market_location': marketLocation, 'test_months': testMonths}) as Map<String, dynamic>);

  // formulations
  Future<String> generate({
    required int flockId,
    required String location,
    required String method,
    required String priceMode,
    int horizon = 1,
    int? population,
    int? generations,
  }) async {
    final body = <String, dynamic>{
      'flock_id': flockId,
      'market_location': location,
      'method': method,
      'price_mode': priceMode,
      'forecast_horizon_months': horizon,
    };
    if (population != null) body['population_size'] = population;
    if (generations != null) body['max_generations'] = generations;
    final data = await client.postJson('/formulations/generate', body)
        as Map<String, dynamic>;
    return data['job_id'] as String;
  }

  Future<JobResult> job(String jobId) async =>
      JobResult.fromJson(await client.get('/formulations/jobs/$jobId')
          as Map<String, dynamic>);

  Future<FormulationDetail> formulation(int id) async =>
      FormulationDetail.fromJson(
          await client.get('/formulations/$id') as Map<String, dynamic>);

  Future<List<FormulationSummary>> history(int flockId) async {
    final list = await client.get('/formulations/flocks/$flockId/history') as List;
    return list
        .map((e) => FormulationSummary.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<FormulationDetail> select(int id) async =>
      FormulationDetail.fromJson(await client.postJson(
          '/formulations/$id/select', {}) as Map<String, dynamic>);
}
