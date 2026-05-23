# FaceSDK Web 管理界面

基于 Vue 3 + Element Plus 的人脸识别管理界面，支持中英文切换。

## 功能特性

- 🎯 **人脸检测** - 上传图片检测人脸位置和特征
- 🔍 **人脸比对** - 比对两张人脸图片的相似度
- 🔎 **人脸搜索** - 在人脸库中搜索相似人脸
- 📁 **人脸库管理** - 创建/删除人脸库，添加/删除人脸
- 🌐 **中英文切换** - 完整的国际化支持
- ⚙️ **系统设置** - 配置 API 地址和密钥

## 技术栈

- Vue 3 (Composition API)
- Vue Router 4
- Vue I18n 9
- Element Plus
- Axios

## 安装运行

```bash
# 安装依赖
npm install

# 开发模式运行
npm run serve

# 生产构建
npm run build
```

## 配置

在设置页面配置：
- API 地址：默认 `http://localhost:8000`
- API 密钥：您的 CompreFace API Key

## 项目结构

```
src/
├── api/              # API 接口
├── components/       # 组件
│   ├── AppHeader.vue # 顶部导航（含语言切换）
│   └── AppLayout.vue # 布局组件
├── locales/          # 国际化文件
│   ├── zh.json       # 中文
│   └── en.json       # 英文
├── router/           # 路由配置
├── views/            # 页面视图
│   ├── HomeView.vue
│   ├── DetectView.vue
│   ├── CompareView.vue
│   ├── SearchView.vue
│   ├── SubjectsView.vue
│   └── SettingsView.vue
├── App.vue
├── i18n.js           # i18n 配置
└── main.js           # 入口文件
```

## 国际化

语言切换器位于顶部导航栏右侧，支持：
- 简体中文
- English

语言设置会自动保存到 localStorage。

## 开发说明

### 添加新语言

1. 在 `src/locales/` 下创建新的 JSON 文件
2. 在 `src/i18n.js` 中导入并添加到 messages
3. 在 `AppHeader.vue` 的语言下拉菜单中添加选项

### API 接口

所有 API 调用通过 `src/api/face.js` 统一管理，自动读取 localStorage 中的 API Key。
