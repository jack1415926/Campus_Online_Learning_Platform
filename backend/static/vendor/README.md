# 本地前端资源

为实验周离线演示保留原有固定版本，不增加前端构建工具。资源来自对应版本的 unpkg npm 包；许可证随目录保存，Element Plus 许可证来自官方仓库 `2.9.1` 标签的 `LICENSE`。

| 目录 | npm 包与版本 | 许可证 |
|---|---|---|
| vue-3.5.13 | vue@3.5.13 | MIT |
| element-plus-2.9.1 | element-plus@2.9.1 | MIT |
| icons-vue-2.3.1 | @element-plus/icons-vue@2.3.1 | MIT |
| pdfjs-2.16.105 | pdfjs-dist@2.16.105 | Apache-2.0 |

`index.html` 直接引用本地 JS/CSS，PDF worker 也指向本地文件。图标包使用 SVG 组件，不需要额外图标 CSS。不要移除许可证文件。
