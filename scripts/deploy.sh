#!/bin/bash
#
# Arboris Novel 一键部署脚本
# 适用于全新服务器的快速部署
#
# 使用方法:
#   chmod +x deploy.sh
#   ./deploy.sh
#

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 打印分隔线
print_separator() {
    echo "========================================================================"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查 Python 版本
check_python() {
    log_info "检查 Python 版本..."
    if ! command_exists python3; then
        log_error "未找到 Python 3，请先安装 Python 3.9+"
        exit 1
    fi

    python_version=$(python3 --version | cut -d' ' -f2)
    log_success "Python 版本: $python_version"
}

# 检查 Node.js 版本
check_nodejs() {
    log_info "检查 Node.js 版本..."
    if ! command_exists node; then
        log_error "未找到 Node.js，请先安装 Node.js 20.19.0+"
        exit 1
    fi

    node_version=$(node --version)
    log_success "Node.js 版本: $node_version"
}

# 检查 npm 版本
check_npm() {
    log_info "检查 npm 版本..."
    if ! command_exists npm; then
        log_error "未找到 npm，请先安装 npm"
        exit 1
    fi

    npm_version=$(npm --version)
    log_success "npm 版本: $npm_version"
}

# 获取项目根目录
# 脚本位于项目的 scripts/ 目录内，因此需要回到上一层
PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# 主函数
main() {
    print_separator
    echo -e "${GREEN}Arboris Novel 一键部署脚本${NC}"
    print_separator
    echo ""

    log_info "项目目录: $PROJECT_DIR"
    echo ""

    # 1. 系统检查
    print_separator
    log_info "步骤 1/6: 系统依赖检查"
    print_separator
    check_python
    check_nodejs
    check_npm
    log_success "系统依赖检查完成"
    echo ""

    # 2. 后端部署
    print_separator
    log_info "步骤 2/6: 部署后端"
    print_separator

    cd "$BACKEND_DIR"

    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        log_info "创建 Python 虚拟环境..."
        python3 -m venv venv
        log_success "虚拟环境创建完成"
    else
        log_warning "虚拟环境已存在，跳过创建"
    fi

    # 激活虚拟环境
    log_info "激活虚拟环境..."
    source venv/bin/activate

    # 安装依赖
    log_info "安装 Python 依赖..."
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    log_success "Python 依赖安装完成"

    # 检查 .env 文件
    if [ ! -f ".env" ]; then
        log_warning ".env 文件不存在，这不应该发生（代码已包含 .env）"
        log_info "请手动编辑 backend/.env 文件，配置 LLM API Key"
    else
        log_success ".env 文件已存在"
        log_warning "请确认已配置 LLM API Key（OPENAI_API_KEY 或 GEMINI_API_KEY）"
    fi

    # 创建必要目录
    log_info "创建必要目录..."
    mkdir -p storage logs
    log_success "目录创建完成"

    log_success "后端部署完成"
    echo ""

    # 3. 前端部署
    print_separator
    log_info "步骤 3/6: 部署前端"
    print_separator

    cd "$FRONTEND_DIR"

    # 安装依赖
    log_info "安装前端依赖（这可能需要几分钟）..."
    npm install
    log_success "前端依赖安装完成"

    log_success "前端部署完成"
    echo ""

    # 4. 测试后端启动
    print_separator
    log_info "步骤 4/6: 测试后端启动"
    print_separator

    cd "$BACKEND_DIR"
    source venv/bin/activate

    log_info "测试后端配置..."
    if python3 -c "from app.core.config import settings; print(f'配置加载成功: {settings.app_name}')" 2>/dev/null; then
        log_success "后端配置加载成功"
    else
        log_error "后端配置加载失败，请检查 .env 文件"
        log_warning "最常见的问题是未配置 LLM API Key"
        exit 1
    fi

    log_success "后端测试完成"
    echo ""

    # 5. 生成 systemd 服务文件
    print_separator
    log_info "步骤 5/6: 生成 systemd 服务配置"
    print_separator

    USER=$(whoami)

    log_info "生成服务文件..."

    # 生成 API 服务文件
    sed "s|{{PROJECT_DIR}}|$PROJECT_DIR|g; s|{{USER}}|$USER|g" \
        "$BACKEND_DIR/deployment/arboris-api.service" > /tmp/arboris-api.service

    # 生成异步处理器服务文件
    sed "s|{{PROJECT_DIR}}|$PROJECT_DIR|g; s|{{USER}}|$USER|g" \
        "$BACKEND_DIR/deployment/arboris-async-processor.service" > /tmp/arboris-async-processor.service

    log_success "服务文件已生成到 /tmp/ 目录"
    log_info "如需安装系统服务，请运行以下命令："
    echo ""
    echo "  sudo mkdir -p /var/log/arboris"
    echo "  sudo chown $USER:$USER /var/log/arboris"
    echo "  sudo cp /tmp/arboris-api.service /etc/systemd/system/"
    echo "  sudo cp /tmp/arboris-async-processor.service /etc/systemd/system/"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl start arboris-api"
    echo "  sudo systemctl enable arboris-api"
    echo "  sudo systemctl start arboris-async-processor"
    echo "  sudo systemctl enable arboris-async-processor"
    echo ""

    # 6. 部署完成
    print_separator
    log_info "步骤 6/6: 部署总结"
    print_separator

    echo ""
    log_success "🎉 Arboris Novel 部署完成！"
    echo ""
    echo "接下来的步骤："
    echo ""
    echo "1. 📝 配置 LLM API Key（必需）"
    echo "   编辑: $BACKEND_DIR/.env"
    echo "   设置: OPENAI_API_KEY 或 GEMINI_API_KEY 或 DEEPSEEK_API_KEY"
    echo ""
    echo "2. 🚀 启动服务（开发模式）"
    echo "   后端: cd $BACKEND_DIR && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"
    echo "   前端: cd $FRONTEND_DIR && npm run dev"
    echo ""
    echo "3. 🌐 访问应用"
    echo "   前端: http://localhost:5173"
    echo "   后端: http://localhost:8000"
    echo "   健康检查: curl http://localhost:8000/health"
    echo ""
    echo "4. 👤 默认管理员账号"
    echo "   用户名: admin"
    echo "   密码: ChangeMe123!"
    echo "   ⚠️  请登录后立即修改密码"
    echo ""
    echo "5. 📚 生产部署"
    echo "   参考: $PROJECT_DIR/DEPLOYMENT.md"
    echo "   配置 systemd 服务、Nginx、HTTPS 等"
    echo ""

    print_separator
    log_info "更多帮助请查看 DEPLOYMENT.md 文档"
    print_separator
}

# 运行主函数
main
