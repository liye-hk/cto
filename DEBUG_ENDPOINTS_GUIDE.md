# Debug HTML Endpoints - User Guide

## 概述 (Overview)

为了帮助诊断EPUB转PDF过程中的字体大小、颜色和格式问题，我们添加了调试功能，允许用户查看和下载转换过程中生成的HTML文档。

To help diagnose font size, color, and formatting issues during EPUB to PDF conversion, we've added debug functionality that allows users to view and download the HTML document generated during conversion.

## 功能说明 (Features)

每次转换EPUB文件时，系统会自动保存一份生成的HTML文档到 `/tmp/debug.html`。用户可以通过以下三个API端点访问这个文件：

Every time an EPUB file is converted, the system automatically saves the generated HTML document to `/tmp/debug.html`. Users can access this file through three API endpoints:

### 1. `/api/debug-info` - 获取调试信息

**用途**: 检查debug.html文件是否存在，获取文件大小和内容预览

**Usage**: Check if debug.html exists, get file size and content preview

**访问方式**:
```bash
curl http://your-domain/api/debug-info
```

**返回示例** (文件存在时):
```json
{
  "file_exists": true,
  "file_size": "45678 bytes",
  "file_size_kb": "44.61 KB",
  "preview": "<!DOCTYPE html><html><head>...",
  "download_url": "/api/download-debug",
  "view_url": "/api/debug-html",
  "message": "Debug HTML 文件已生成，可以查看或下载"
}
```

**返回示例** (文件不存在时):
```json
{
  "file_exists": false,
  "message": "需要先转换一个 EPUB 文件",
  "info": "上传 EPUB 文件后，系统会自动生成 debug.html 用于诊断"
}
```

### 2. `/api/debug-html` - 在浏览器中查看HTML

**用途**: 直接在浏览器中查看生成的HTML，可以看到字体大小、颜色、对齐等效果

**Usage**: View the generated HTML directly in browser to see font sizes, colors, alignment, etc.

**访问方式**:
- 浏览器访问: `http://your-domain/api/debug-html`
- 或使用curl: `curl http://your-domain/api/debug-html`

**优点**:
- ✅ 可以直接看到字体大小是否正确
- ✅ 可以检查颜色是否被正确应用
- ✅ 可以验证段落缩进和对齐
- ✅ 可以检查图片嵌入情况

### 3. `/api/download-debug` - 下载HTML文件

**用途**: 下载HTML文件到本地，用编辑器或浏览器打开详细分析

**Usage**: Download the HTML file to local machine for detailed analysis

**访问方式**:
```bash
curl http://your-domain/api/download-debug -o debug.html
```

**或在浏览器中直接访问**:
```
http://your-domain/api/download-debug
```

## 使用流程 (Workflow)

### Step 1: 转换EPUB文件
首先上传并转换一个EPUB文件：

```bash
curl -X POST \
  -F "file=@your-book.epub" \
  http://your-domain/api/convert \
  -o output.pdf
```

或者使用网页界面上传。

### Step 2: 检查调试信息
确认debug.html已生成：

```bash
curl http://your-domain/api/debug-info
```

### Step 3: 查看或下载HTML

**选项A: 浏览器查看**
在浏览器中打开:
```
http://your-domain/api/debug-html
```

**选项B: 下载到本地**
```bash
curl http://your-domain/api/download-debug -o debug.html
```

然后用浏览器或文本编辑器打开 `debug.html` 文件。

## 诊断用途 (Diagnostic Use Cases)

### 1. 检查字体大小 (Font Size)
打开debug.html，在浏览器中检查文本是否太小或太大。
可以使用浏览器的检查工具查看CSS样式。

### 2. 检查颜色显示 (Color Display)
查看HTML中是否有 `color` 属性或 `style="color: ..."` 标记。
验证颜色代码是否正确嵌入。

### 3. 检查段落缩进 (Paragraph Indentation)
查看 `<p>` 标签的 `text-indent` CSS样式。
应该是 `2em`（约等于2个中文字符宽度）。

### 4. 检查居中对齐 (Center Alignment)
查找 `align="center"` 属性和 `style="text-align: center;"` 标记。
验证居中样式是否被正确应用。

### 5. 检查图片嵌入 (Image Embedding)
查看 `<img>` 标签的 `src` 属性。
应该是 `data:image/...;base64,...` 格式（Base64嵌入）。

### 6. 检查封面显示 (Cover Page)
查找 `<section class="cover-page">` 标签。
验证封面图片是否存在且尺寸正确。

## 注意事项 (Important Notes)

⚠️ **文件会被覆盖**: 每次转换新的EPUB文件时，debug.html会被覆盖。只保留最新一次转换的调试文件。

⚠️ **File Overwrites**: Each time a new EPUB is converted, debug.html is overwritten. Only the most recent conversion's debug output is kept.

⚠️ **仅限诊断用途**: 这个HTML文件是用于诊断的，不是最终的PDF输出。PDF渲染可能与浏览器显示略有差异。

⚠️ **Diagnostic Only**: This HTML file is for diagnostic purposes. PDF rendering may differ slightly from browser display.

## 故障排查 (Troubleshooting)

### 问题: 访问 `/api/debug-html` 返回404错误

**原因**: 还没有转换过任何EPUB文件，debug.html尚未生成。

**解决方案**: 先转换一个EPUB文件，然后再访问debug端点。

### 问题: HTML中看不到颜色

**检查步骤**:
1. 在HTML源代码中搜索 `color`
2. 检查是否有 `<font color="...">` 或 `<span style="color: ...">`
3. 如果没有，说明原EPUB文件中可能没有颜色信息

### 问题: 字体大小不正确

**检查步骤**:
1. 打开debug.html，查看 `<style>` 标签中的CSS
2. 检查 `body { font-size: ... }` 的值（应该是13pt）
3. 检查 `h1`, `h2`, `h3` 的字体大小
4. 如果不正确，需要修改 `app/services/converter.py` 中的 `CSS_STYLES`

## API响应状态码 (Response Status Codes)

| 端点 | 成功 | 失败 |
|------|------|------|
| `/api/debug-info` | 200 OK | 500 Internal Server Error |
| `/api/debug-html` | 200 OK | 404 Not Found |
| `/api/download-debug` | 200 OK | 404 Not Found |

## 示例代码 (Example Code)

### Python示例:

```python
import requests

# Convert EPUB
files = {'file': open('book.epub', 'rb')}
response = requests.post('http://localhost:8000/api/convert', files=files)

if response.status_code == 200:
    # Save PDF
    with open('output.pdf', 'wb') as f:
        f.write(response.content)
    
    # Get debug info
    debug_info = requests.get('http://localhost:8000/api/debug-info').json()
    print(f"Debug file size: {debug_info['file_size_kb']}")
    
    # Download debug HTML
    debug_html = requests.get('http://localhost:8000/api/download-debug')
    with open('debug.html', 'wb') as f:
        f.write(debug_html.content)
    print("Debug HTML saved to debug.html")
```

### JavaScript示例:

```javascript
async function convertAndDebug(file) {
  // Convert EPUB
  const formData = new FormData();
  formData.append('file', file);
  
  const convertResponse = await fetch('/api/convert', {
    method: 'POST',
    body: formData
  });
  
  if (convertResponse.ok) {
    // Download PDF
    const blob = await convertResponse.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'output.pdf';
    a.click();
    
    // Get debug info
    const debugInfo = await fetch('/api/debug-info').then(r => r.json());
    console.log('Debug file info:', debugInfo);
    
    // Open debug HTML in new tab
    window.open('/api/debug-html', '_blank');
  }
}
```

## 技术实现细节 (Technical Implementation)

### 文件位置
- Debug HTML文件存储在: `/tmp/debug.html`
- 每次转换时自动生成和覆盖

### 代码位置
- HTML生成代码: `app/services/converter.py` - `convert()` 方法
- API端点代码: `app/api/routes.py` - 三个debug端点
- 测试代码: `tests/test_debug_endpoints.py`

### 生成时机
在 `EPUBToPDFConverter.convert()` 方法中，HTML文档构建完成后、PDF渲染之前保存。

```python
# Build HTML document
html_content = self._build_html_document(epub_book)

# Save debug HTML for inspection
try:
    with open('/tmp/debug.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    logger.info("Debug HTML saved to /tmp/debug.html")
except Exception as e:
    logger.warning(f"Failed to save debug.html: {e}")
```

## 反馈 (Feedback)

如果您在使用调试功能时遇到问题，或有改进建议，请提交Issue。

If you encounter issues using the debug functionality or have suggestions for improvement, please submit an Issue.
