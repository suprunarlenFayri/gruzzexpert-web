import 'package:dio/dio.dart';

import '../config/app_config.dart';
import 'api_client.dart';

class TaskCard {
  TaskCard({
    required this.id,
    required this.title,
    required this.price,
    required this.status,
    this.description,
    this.city,
    this.address,
    this.executionDate,
    this.executionTime,
    this.assignedCount = 0,
    this.requiredWorkers = 1,
    this.chatId,
  });

  final int id;
  final String title;
  final double price;
  final String status;
  final String? description;
  final String? city;
  final String? address;
  final String? executionDate;
  final String? executionTime;
  final int assignedCount;
  final int requiredWorkers;
  final int? chatId;

  factory TaskCard.fromJson(Map<String, dynamic> j) => TaskCard(
        id: j['id'] as int,
        title: (j['title'] ?? '').toString(),
        price: (j['price'] as num?)?.toDouble() ?? 0,
        status: (j['status'] ?? 'recruiting').toString(),
        description: j['description']?.toString(),
        city: j['city']?.toString(),
        address: j['address']?.toString(),
        executionDate: j['execution_date']?.toString(),
        executionTime: j['execution_time']?.toString(),
        assignedCount: (j['assigned_count'] as num?)?.toInt() ?? 0,
        requiredWorkers: (j['required_workers'] as num?)?.toInt() ?? 1,
        chatId: (j['chat_id'] as num?)?.toInt(),
      );
}

class TaskDetail extends TaskCard {
  TaskDetail({
    required super.id,
    required super.title,
    required super.price,
    required super.status,
    super.description,
    super.city,
    super.address,
    super.executionDate,
    super.executionTime,
    super.assignedCount,
    super.requiredWorkers,
    super.chatId,
    this.canTake = false,
    this.canReject = false,
    this.rejectBlockReason,
    this.userTracking,
  });

  final bool canTake;
  final bool canReject;
  final String? rejectBlockReason;
  final Map<String, dynamic>? userTracking;

  factory TaskDetail.fromJson(Map<String, dynamic> j) => TaskDetail(
        id: j['id'] as int,
        title: (j['title'] ?? '').toString(),
        price: (j['price'] as num?)?.toDouble() ?? 0,
        status: (j['status'] ?? 'recruiting').toString(),
        description: j['description']?.toString(),
        city: j['city']?.toString(),
        address: j['address']?.toString(),
        executionDate: j['execution_date']?.toString(),
        executionTime: j['execution_time']?.toString(),
        assignedCount: (j['assigned_count'] as num?)?.toInt() ?? 0,
        requiredWorkers: (j['required_workers'] as num?)?.toInt() ?? 1,
        chatId: (j['chat_id'] as num?)?.toInt(),
        canTake: j['can_take'] == true,
        canReject: j['can_reject_assignment'] == true,
        rejectBlockReason: j['reject_block_reason']?.toString(),
        userTracking: j['user_tracking'] as Map<String, dynamic>?,
      );
}

class TasksApi {
  TasksApi(this._client);

  final ApiClient _client;

  Future<({List<TaskCard> pool, List<TaskCard> my})> fetchLists() async {
    final res = await _client.dio.get('/tasks');
    final data = res.data as Map<String, dynamic>;
    if (data['ok'] != true) {
      throw DioException(requestOptions: res.requestOptions, message: data['error']?.toString());
    }
    List<TaskCard> parseList(String key) {
      final list = data[key] as List<dynamic>? ?? [];
      return list.map((e) => TaskCard.fromJson(Map<String, dynamic>.from(e as Map))).toList();
    }
    return (pool: parseList('tasks'), my: parseList('my_tasks'));
  }

  Future<TaskDetail> fetchDetail(int taskId) async {
    final res = await _client.dio.get('/tasks/$taskId');
    final data = res.data as Map<String, dynamic>;
    if (data['ok'] != true) {
      throw DioException(requestOptions: res.requestOptions, message: data['error']?.toString());
    }
    return TaskDetail.fromJson(Map<String, dynamic>.from(data['task'] as Map));
  }

  Future<void> postStatus(int taskId, String status) async {
    final res = await _client.rootDio.post(
      AppConfig.apiPath('/api/tasks/$taskId/status'),
      data: {'status': status},
    );
    final data = res.data as Map<String, dynamic>;
    if (data['ok'] != true) {
      throw DioException(requestOptions: res.requestOptions, message: data['error']?.toString());
    }
  }

  Future<void> takeTask(int taskId) async => postStatus(taskId, 'accept');

  Future<void> rejectTask(int taskId) async => postStatus(taskId, 'reject');
}
