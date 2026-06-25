# ClaudePilot UI 风格指南（Numina 适配版）

本项目的视觉风格基于 **Numina UI** 设计系统，目标是：深色 sidebar 提供视觉锚点，浅色内容区使用 Neumorphism（拟态）营造物理层级感，叠加 subtle 科技感动效增加界面活力。

## 设计原则

1. **无硬边框**：`--border: transparent`，层级靠阴影和圆角区分。
2. **圆角统一**：主要组件使用 `rounded-xl`（16px）。
3. **拟态阴影**：浅色区使用 `#ffffff` / `#c5c9ce` 两套阴影。
4. **科技感动效要 subtle**：动画时长 2-4s，opacity 低，不抢视线。
5. **响应式优先**：组件需同时支持桌面和移动端。
6. **新增 UI 优先使用 Numina 组件**，不直接写裸 Tailwind class。

## 配色系统

### 内容区（浅色拟态背景）

| Token                | 色值          | 用途           |
| -------------------- | ------------- | -------------- |
| `--background`       | `#e8ecf1`     | 页面背景       |
| `--card`             | `#e8ecf1`     | 卡片/面板背景  |
| `--foreground`       | `#4a5568`     | 主文字         |
| `--muted-foreground` | `#5a6b7d`     | 次要文字       |
| `--primary`          | `#4f46e5`     | 主色调（靛蓝） |
| `--destructive`      | `#ef4444`     | 危险/删除      |
| `--border`           | `transparent` | 边框（透明）   |
| `--input`            | `#e8ecf1`     | 输入框背景     |
| `--ring`             | `#4f46e5`     | focus ring     |

### Sidebar（深色）

| Tailwind class       | 对应变量                | 用途         |
| -------------------- | ----------------------- | ------------ |
| `bg-sidebar-bg`      | `--sidebar-bg: #1e293b` | sidebar 背景 |
| `text-sidebar-fg`    | `--sidebar-fg: #f1f5f9` | 主文字       |
| `text-sidebar-muted` | `--sidebar-muted`       | 次要文字     |
| `bg-sidebar-active`  | `--sidebar-active-bg`   | 当前项背景   |
| `bg-sidebar-hover`   | `--sidebar-hover-bg`    | hover 背景   |

## 拟态阴影

通过 CSS 变量和 Tailwind 自定义 `boxShadow` 使用：

| 变量 / Tailwind class               | 用途            |
| ----------------------------------- | --------------- |
| `--neu-raised` / `shadow-neu`       | 卡片/面板凸起   |
| `--neu-raised-sm` / `shadow-neu-sm` | 按钮/小元素凸起 |
| `--neu-pressed-sm`                  | 输入框凹陷      |

示例：

```tsx
<div
  className="rounded-xl bg-card p-6"
  style={{ boxShadow: "var(--neu-raised)" }}
>
  Content
</div>
```

## 组件清单

### Button

- 位置：`frontend/src/components/ui/button.tsx`
- 主按钮：`variant="default"`，靛蓝背景、白色文字、rounded-xl、拟态阴影、hover 白光扫过。
- 危险按钮：`variant="destructive"`。
- 其他变体保留 shadcn 语义但使用 rounded-xl。

```tsx
import { Button } from "@/components/ui";

<Button variant="default" size="sm">
  Save
</Button>;
```

### NuminaButton

- 位置：`frontend/src/components/ui/numina-button.tsx`
- 更"Numina 原生"的按钮，带 6px 凸起大阴影，用于营销/CTA 场景。

```tsx
import { NuminaButton } from "@/components/ui";

<NuminaButton variant="primary">Start</NuminaButton>;
```

### NuminaCard

- 位置：`frontend/src/components/ui/numina-card.tsx`
- 无 border、rounded-xl、拟态凸起阴影、hover 微抬升。

```tsx
import { NuminaCard } from "@/components/ui";

<NuminaCard>...</NuminaCard>;
```

### NuminaInput

- 位置：`frontend/src/components/ui/numina-input.tsx`
- 凹陷拟态输入框，focus 时有 glow。

```tsx
import { NuminaInput } from "@/components/ui";

<NuminaInput placeholder="Search..." />;
```

### Textarea

- 位置：`frontend/src/components/ui/textarea.tsx`
- 同样使用凹陷拟态风格。

## 动画工具类

| Class               | 效果                    |
| ------------------- | ----------------------- |
| `tech-glow`         | 靛蓝 glow pulse（3s）   |
| `tech-glow-fast`    | 快速 glow pulse（1.5s） |
| `tech-btn-shimmer`  | 按钮 hover 白光扫过     |
| `tech-data-flicker` | 数据微闪烁              |
| `tech-bg-particles` | 背景径向光晕浮动        |

## 页面布局约定

```tsx
<div className="flex h-screen bg-background text-foreground tech-bg-particles">
  <aside className="w-64 bg-sidebar-bg text-sidebar-fg">...</aside>
  <main className="relative z-10 flex-1 p-4">...</main>
</div>
```

注意：

- `tech-bg-particles` 会生成绝对定位的光晕层，主内容区需要加 `relative z-10` 才能交互。
- Sidebar 导航项当前激活态使用 `bg-sidebar-active text-sidebar-fg tech-glow`。

## 无障碍

- 所有文字与背景对比度 ≥ 4.5:1。
- 动画支持 `prefers-reduced-motion`：在 `index.css` 末尾已统一禁用。

## 参考

- Numina UI skill 源文件：`~/.claude/skills/numina-ui-style/components/`
