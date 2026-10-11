# 若依集成示例

针对 RuoYi-Vue 的 Spring 5 / Java 11 宿主，示例需复制到宿主对应 package 并添加 FaceSDK 依赖、配置。SysUser 使用 `com.ruoyi.common.core.domain.entity.SysUser`。

所有 `/face` 接口要求登录，宿主必须启用 `@EnableGlobalMethodSecurity(prePostEnabled = true)`，不得将 `/face/**` 加入匿名白名单。注册默认使用当前登录 ID；提交其他用户 ID 会被拒绝。删除与查询在服务层检查当前用户所有权，禁止操作他人绑定。需要管理员代办时应另设接口，配置明确权限并检查宿主数据范围。

`/face/login` 保留旧路由作为已登录用户的人脸验证入口：要求单脸、匹配当前用户，且用户未禁用/删除。只返回 userId、userName、verified、similarity，不返回裸 SysUser，不签发 token。它不能直接取代宿主登录服务；真正登录/MFA 需通过宿主认证流程实施，并配置限流和经过验证的活体检测方案。

从环境配置三种服务密钥。FaceService 不向 CompreFace 传 metadata，也不覆写 SysUser.remark。Subject `user_<id>` 是绑定索引；显示名称、注册审计、额外元数据应另建应用表。添加人脸自动创建 Subject；写入失败直接返回失败。

独立测试在 `tests/ruoyi`，使用真实 Spring 依赖及仅限测试的 RuoYi 边界桩，覆盖所有权、控制器当前用户 ID、多脸、禁用/删除用户和响应字段。根目录执行：

```sh
mvn -f sdk/java/pom.xml install
mvn -f tests/ruoyi/pom.xml verify
```

这些测试验证示例业务逻辑与编译，不代表已经在完整若依宿主中验证 JWT、Spring Security 过滤链或数据权限。
