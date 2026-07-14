# -*- coding: utf-8 -*-
"""
泡泡堂家族比赛积分竞猜系统 - 主界面

@author hyq
@version 2026-07-13
"""

import os
import sys
from typing import Any

from PyQt6.QtCore import Qt, QMimeData, QPoint, QSize
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QDrag, QPainter, QBrush, QPen,
    QPixmap, QIcon, QAction
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QPushButton, QSpinBox,
    QTableWidget, QTableWidgetItem, QSplitter, QGroupBox, QMessageBox,
    QInputDialog, QHeaderView, QTabWidget, QMenu, QFileDialog,
    QAbstractItemView, QFrame, QSizePolicy, QDialog, QFormLayout,
    QLineEdit, QDialogButtonBox, QStyle, QScrollArea
)

from src.database.db_manager import DBManager
from src.database.repository import Repository
from src.database.models import (
    Member, Tournament, Round, Bet, MatchHistory,
    TeamColor, TournamentStatus
)
from src.engine.betting_engine import (
    validate_bet, validate_match_score, validate_team_bindings,
    calculate_settlement, BetValidationError, MatchResultValidationError,
    TeamBindingValidationError
)


# ────────────────────────────────────────────────────────────────────
# 样式表常量
# ────────────────────────────────────────────────────────────────────

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Microsoft YaHei UI", "微软雅黑", sans-serif;
}
QGroupBox {
    border: 1px solid #3a3a5c;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 20px;
    font-weight: bold;
    font-size: 13px;
    color: #c0c0e0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QListWidget {
    background-color: #16213e;
    border: 1px solid #3a3a5c;
    border-radius: 6px;
    color: #e0e0e0;
    font-size: 13px;
    padding: 4px;
}
QListWidget::item {
    background-color: #252849;
    border: 1px solid #3a3f73;
    border-radius: 6px;
    padding: 6px 8px;
    margin: 2px;
}
QListWidget::item:hover {
    background-color: #3b407a;
    border: 1px solid #4f55a3;
}
QListWidget::item:selected {
    background-color: #4a5099;
    border: 1px solid #636bc7;
}
QTableWidget {
    background-color: #16213e;
    border: 1px solid #3a3a5c;
    border-radius: 6px;
    color: #e0e0e0;
    gridline-color: #2a2a4e;
    font-size: 12px;
}
QTableWidget::item {
    padding: 4px;
}
QHeaderView::section {
    background-color: #0f3460;
    color: #e0e0e0;
    padding: 6px;
    border: 1px solid #3a3a5c;
    font-weight: bold;
    font-size: 12px;
}
QPushButton {
    background-color: #0f3460;
    color: #e0e0e0;
    border: 1px solid #3a3a5c;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: bold;
    min-height: 28px;
}
QPushButton:hover {
    background-color: #1a4a7a;
}
QPushButton:pressed {
    background-color: #0a2a4a;
}
QPushButton:disabled {
    background-color: #2a2a3e;
    color: #666;
}
QSpinBox {
    background-color: #16213e;
    border: 1px solid #3a3a5c;
    border-radius: 4px;
    color: #e0e0e0;
    padding: 4px 8px;
    font-size: 14px;
    min-height: 28px;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #0f3460;
    border: 1px solid #3a3a5c;
    width: 20px;
}
QLabel {
    color: #e0e0e0;
}
QTabWidget::pane {
    border: 1px solid #3a3a5c;
    border-radius: 4px;
    background: #16213e;
}
QTabBar::tab {
    background-color: #0f3460;
    color: #c0c0e0;
    padding: 8px 16px;
    border: 1px solid #3a3a5c;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
    min-width: 100px;
}
QTabBar::tab:selected {
    background-color: #16213e;
    color: #ffffff;
}
QSplitter::handle {
    background-color: #3a3a5c;
    height: 3px;
}
QScrollBar:vertical {
    background: #1a1a2e;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #3a3a5c;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""


# ────────────────────────────────────────────────────────────────────
# 支持拖拽的自定义 QListWidget
# ────────────────────────────────────────────────────────────────────

class DragListWidget(QListWidget):
    """
    支持拖出的列表 (可用于成员大池或游戏账号选手大池)

    @author hyq
    @version 2026-07-13
    """

    def __init__(self, pool_type: str = "member", parent: QWidget | None = None):
        super().__init__(parent)
        self.pool_type = pool_type  # "member" 或 "player"
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        
        # 彻底抛弃 IconMode 拖动陷阱！改用 ListMode 并开启 LeftToRight 流式换行
        # 这样既能实现一排排紧凑展示（ID自适应宽度），又 100% 完美支持 Qt 原生拖放
        self.setViewMode(QListWidget.ViewMode.ListMode)
        self.setFlow(QListWidget.Flow.LeftToRight)
        self.setWrapping(True)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSpacing(6)
        self.setWordWrap(True)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.adjust_items_size()

    def adjust_items_size(self) -> None:
        """根据最新渲染出的物理宽度，重新设置大池中每一个项的 sizeHint，消灭隐藏 TabWidget 导致初始缩水成 ... 的缺陷"""
        count = self.count()
        if count == 0:
            return
            
        font = QFont("Microsoft YaHei UI", 12)
        from PyQt6.QtGui import QFontMetrics
        metrics = QFontMetrics(font)
        
        for i in range(count):
            item = self.item(i)
            if item:
                text = item.text()
                # 根据真实文本宽度加气泡裕度
                width = metrics.horizontalAdvance(text) + 45
                item.setSizeHint(QSize(width, 32))

    def startDrag(self, supportedActions: Qt.DropAction) -> None:
        """原生系统拖拽虚函数，极度稳定"""
        item = self.currentItem()
        if not item:
            return
            
        drag = QDrag(self)
        mime = QMimeData()
        name = item.data(Qt.ItemDataRole.UserRole)
        
        if self.pool_type == "member":
            mime.setText(f"MEMBER|{name}")
        else:
            mime.setText(f"PLAYER|{name}")
            
        drag.setMimeData(mime)

        pixmap = QPixmap(140, 30)
        pixmap.fill(QColor(30, 30, 60, 200))
        painter = QPainter(pixmap)
        painter.setPen(QColor(224, 224, 224))
        painter.setFont(QFont("Microsoft YaHei UI", 10))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, str(name))
        painter.end()
        drag.setPixmap(pixmap)

        result = drag.exec(Qt.DropAction.MoveAction)
        if result == Qt.DropAction.MoveAction:
            try:
                row = self.row(item)
                if row >= 0:
                    self.takeItem(row)
            except RuntimeError:
                # 若 item 包装的 C++ 对象已被销毁（例如由于大池/活跃池被重新 clear 并重构刷新），直接安全忽略即可
                pass

    def mouseReleaseEvent(self, event) -> None:
        item = self.itemAt(event.position().toPoint())
        if item:
            rect = self.visualItemRect(item)
            if event.position().x() > rect.right() - 40:
                name = item.data(Qt.ItemDataRole.UserRole)
                reply = QMessageBox.question(
                    self, "🗑️ 确认物理删除",
                    f"您确定要将「{name}」从系统数据库中【彻底物理删除】吗？\n（此操作将永久移除该成员/选手，无法恢复！）",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    main_win = self.window()
                    if hasattr(main_win, "_delete_pool_item"):
                        main_win._delete_pool_item(self.pool_type, name)
                return
        super().mouseReleaseEvent(event)


class DropListWidget(QListWidget):
    """
    支持接收拖放的队伍列表

    @author hyq
    @version 2026-07-13
    """

    def __init__(
        self,
        team_color: TeamColor,
        is_player_list: bool,
        main_window: 'MainWindow',
        parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.team_color = team_color
        self.is_player_list = is_player_list
        self.main_window = main_window
        self.setAcceptDrops(True)
        self.setDragEnabled(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # 启用 ListMode 进行流式平铺（横向排版，自动换行），杜绝 IconMode 导致接收端假死拦截拖放！
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setViewMode(QListWidget.ViewMode.ListMode)
        self.setFlow(QListWidget.Flow.LeftToRight)
        self.setWrapping(True)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSpacing(6)
        self.setWordWrap(True)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.adjust_items_size()

    def adjust_items_size(self) -> None:
        """根据当前列表物理宽度，动态限制每个胶囊的宽度，确保每行至少塞下2个胶囊"""
        count = self.count()
        if count == 0:
            return
            
        # 减去滚动条（约16px）和 item 间距与边沿 margin（约18px）
        available_width = self.width() - 34
        if available_width < 100:
            return
            
        # 每个胶囊的最大宽度上限为可用宽度的一半（扣除 18 像素边距和 spacing），保证并排容纳2个以上
        max_item_width = int(available_width / 2) - 18
        
        font = QFont("Microsoft YaHei UI", 11)
        from PyQt6.QtGui import QFontMetrics
        metrics = QFontMetrics(font)
        
        for i in range(count):
            item = self.item(i)
            if item:
                text = item.text()
                # 真实渲染的宽度
                text_w = metrics.horizontalAdvance(text) + 36
                # 宽度限制在 max_item_width 以内，但也不能太窄
                final_w = min(text_w, max_item_width)
                final_w = max(final_w, 90)
                item.setSizeHint(QSize(final_w, 32))

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasText():
            event.accept()
            event.setDropAction(Qt.DropAction.MoveAction)
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasText():
            event.accept()
            event.setDropAction(Qt.DropAction.MoveAction)
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        """处理拖放事件"""
        # 防呆机制：若当前未开启任何赛事，拦截并提示开启赛事
        if self.main_window.current_tournament is None:
            QMessageBox.warning(
                self, "⚠️ 无法投注/指派选手",
                "当前没有进行中的赛事，无法进行下注或指派选手！\n\n请先点击右侧控制台的「🏆 开始新赛事」以开启本届比赛。"
            )
            event.ignore()
            return

        if not event.mimeData().hasText():
            event.ignore()
            return

        text = event.mimeData().text()
        parts = text.split("|")
        if not parts:
            event.ignore()
            return

        type_flag = parts[0]
        
        if type_flag == "MEMBER":
            if len(parts) != 2:
                event.ignore()
                return
            member_name = parts[1]

            # 成员不能拖到选手列表
            if self.is_player_list:
                QMessageBox.warning(
                    self, "⚠️ 拖拽错误",
                    f"「{member_name}」是投注成员，只能拖入投注列表，不能作为参赛选手！"
                )
                event.ignore()
                return

            # 自动弹窗询问投注金额
            max_bet = self.main_window.max_bet_spin.value()
            amount, ok = QInputDialog.getInt(
                self, f"💰 {member_name} 下注",
                f"请输入「{member_name}」的下注金额（5的倍数，上限 {max_bet}）：",
                value=5, min=5, max=max_bet, step=5
            )
            if not ok:
                event.ignore()
                return

            try:
                validate_bet(amount, max_bet)
            except BetValidationError as e:
                QMessageBox.warning(self, "⚠️ 下注无效", str(e))
                event.ignore()
                return

            # 添加到投注列表
            display_text = f"💰 {member_name}  [{amount}分]  ×"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, member_name)
            item.setData(Qt.ItemDataRole.UserRole + 1, amount)
            font = QFont("Microsoft YaHei UI", 11)
            item.setFont(font)
            from PyQt6.QtGui import QFontMetrics
            metrics = QFontMetrics(font)
            width = metrics.horizontalAdvance(display_text) + 45
            item.setSizeHint(QSize(width, 32))
            self.addItem(item)
            self.adjust_items_size()
            self.main_window.active_members_this_tournament.add(member_name)
            self.main_window._refresh_active_pools()
            self.main_window.member_tabs.setCurrentIndex(1)
            event.setDropAction(Qt.DropAction.MoveAction)
            event.acceptProposedAction()

        elif type_flag == "PLAYER":
            if len(parts) != 2:
                event.ignore()
                return
            nickname = parts[1]

            # 实际游戏ID选手不能拖到投注列表
            if not self.is_player_list:
                QMessageBox.warning(
                    self, "⚠️ 拖拽错误",
                    f"选手账号「{nickname}」只能拖入选手列表，不能作为投注人员下注！"
                )
                event.ignore()
                return

            # 添加到选手列表
            display_text = f"⚔️ {nickname}  ×"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, nickname)
            item.setData(Qt.ItemDataRole.UserRole + 1, 0) # 选手无下注分
            font = QFont("Microsoft YaHei UI", 11)
            item.setFont(font)
            from PyQt6.QtGui import QFontMetrics
            metrics = QFontMetrics(font)
            width = metrics.horizontalAdvance(display_text) + 45
            item.setSizeHint(QSize(width, 32))
            self.addItem(item)
            self.adjust_items_size()
            self.main_window.active_players_this_tournament.add(nickname)
            self.main_window._refresh_active_pools()
            self.main_window.player_tabs.setCurrentIndex(1)
            event.acceptProposedAction()
            
        else:
            event.ignore()

    def _show_context_menu(self, pos: QPoint) -> None:
        """右键菜单 - 退回大池"""
        item = self.itemAt(pos)
        if item is None:
            return
        menu = QMenu(self)
        action_return = QAction("↩️ 退回大池", self)
        action_return.triggered.connect(lambda: self._return_to_pool(item))
        menu.addAction(action_return)
        menu.exec(self.mapToGlobal(pos))

    def mouseReleaseEvent(self, event) -> None:
        item = self.itemAt(event.position().toPoint())
        if item:
            rect = self.visualItemRect(item)
            if event.position().x() > rect.right() - 40:
                self._return_to_pool(item)
                return
        super().mouseReleaseEvent(event)

    def _return_to_pool(self, item: QListWidgetItem) -> None:
        """将成员退回大池（带确认以防手滑误触）"""
        name = item.data(Qt.ItemDataRole.UserRole)
        bet_amount = item.data(Qt.ItemDataRole.UserRole + 1) or 0

        # 防手滑二次确认弹窗
        if self.is_player_list:
            title = "🗑️ 移除选手"
            text = f"确定要将参赛选手「{name}」从当前队伍中移除并退回到选手池吗？"
        else:
            title = "🗑️ 取消投注"
            text = f"确定要取消「{name}」的「{bet_amount}分」投注并将积分退回到大池吗？"

        reply = QMessageBox.question(
            self, title, text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # 从当前列表移除
        row = self.row(item)
        self.takeItem(row)

        if self.is_player_list:
            # 退回到选手大池
            self.main_window._add_player_to_pool(name)
        else:
            # 退回到成员大池
            self.main_window._add_member_to_pool(name, bet_amount)
        self.main_window._refresh_active_pools()


# ────────────────────────────────────────────────────────────────────
# 历史轮次详情弹窗
# ────────────────────────────────────────────────────────────────────

class MatchHistoryDetailsDialog(QDialog):
    """
    往期比赛单轮详情弹窗，精细展示对局结果、选手及投注详情

    @author hyq
    @version 2026-07-14
    """
    def __init__(self, history: MatchHistory, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"📜 赛事ID {history.tournament_id} - 第 {history.round_number} 轮详情")
        self.setMinimumSize(700, 600)
        self.resize(780, 680)
        self.setStyleSheet(DARK_STYLE)
        self._build_ui(history)

    def _build_ui(self, h: MatchHistory) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(24, 24, 24, 24)

        # 头部：轮次大字信息
        header_label = QLabel(f"📜 赛事ID: {h.tournament_id}  •  第 {h.round_number} 轮")
        header_label.setFont(QFont("Microsoft YaHei UI", 12))
        header_label.setStyleSheet("color: #88A0C0;")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)

        # 比分大字版卡
        score_layout = QHBoxLayout()
        score_layout.setSpacing(20)
        score_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        red_score_lbl = QLabel(f"🔴 红队\n{h.red_score}")
        red_score_lbl.setFont(QFont("Microsoft YaHei UI", 18, QFont.Weight.Bold))
        red_score_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        vs_lbl = QLabel("VS")
        vs_lbl.setFont(QFont("Outfit", 22, QFont.Weight.Bold))
        vs_lbl.setStyleSheet("color: #718096;")
        vs_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        green_score_lbl = QLabel(f"🟢 绿队\n{h.green_score}")
        green_score_lbl.setFont(QFont("Microsoft YaHei UI", 18, QFont.Weight.Bold))
        green_score_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 根据胜利者给文字涂色
        if h.winner == TeamColor.RED:
            red_score_lbl.setStyleSheet("color: #EF5350; background: rgba(239, 83, 80, 0.15); border: 2px solid #EF5350; border-radius: 12px; padding: 12px 24px;")
            green_score_lbl.setStyleSheet("color: #718096; background: rgba(255, 255, 255, 0.05); border: 1px dashed #4A5568; border-radius: 12px; padding: 12px 24px;")
        else:
            red_score_lbl.setStyleSheet("color: #718096; background: rgba(255, 255, 255, 0.05); border: 1px dashed #4A5568; border-radius: 12px; padding: 12px 24px;")
            green_score_lbl.setStyleSheet("color: #66BB6A; background: rgba(102, 187, 106, 0.15); border: 2px solid #66BB6A; border-radius: 12px; padding: 12px 24px;")

        score_layout.addWidget(red_score_lbl)
        score_layout.addWidget(vs_lbl)
        score_layout.addWidget(green_score_lbl)
        layout.addLayout(score_layout)

        # 庄家本轮盈亏
        profit_color = "#4CAF50" if h.banker_round_profit >= 0 else "#F44336"
        profit_sign = "+" if h.banker_round_profit >= 0 else ""
        banker_profit_lbl = QLabel(f"👑 庄家本局盈亏：{profit_sign}{h.banker_round_profit} 分")
        banker_profit_lbl.setFont(QFont("Microsoft YaHei UI", 14, QFont.Weight.Bold))
        banker_profit_lbl.setStyleSheet(f"color: {profit_color}; background: rgba(30, 41, 59, 0.8); border: 1px solid #334155; border-radius: 8px; padding: 10px;")
        banker_profit_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(banker_profit_lbl)

        # 参赛选手展示
        players_group = QGroupBox("⚔️ 双方对决选手")
        players_layout = QHBoxLayout(players_group)
        players_layout.setSpacing(15)

        red_players_box = QGroupBox("🔴 红队选手")
        red_p_layout = QVBoxLayout(red_players_box)
        red_p_lbl = QLabel(h.red_players or "暂无选手")
        red_p_lbl.setFont(QFont("Microsoft YaHei UI", 11))
        red_p_lbl.setStyleSheet("color: #FFCDD2;")
        red_p_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        red_p_layout.addWidget(red_p_lbl)

        green_players_box = QGroupBox("🟢 绿队选手")
        green_p_layout = QVBoxLayout(green_players_box)
        green_p_lbl = QLabel(h.green_players or "暂无选手")
        green_p_lbl.setFont(QFont("Microsoft YaHei UI", 11))
        green_p_lbl.setStyleSheet("color: #C8E6C9;")
        green_p_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        green_p_layout.addWidget(green_p_lbl)

        players_layout.addWidget(red_players_box)
        players_layout.addWidget(green_players_box)
        layout.addWidget(players_group)

        # 投注清单解析与横向分栏排版
        bets_group = QGroupBox("💰 投注下注细则清单")
        bets_main_layout = QVBoxLayout(bets_group)
        
        bets_columns_layout = QHBoxLayout()
        bets_columns_layout.setSpacing(15)

        red_bets_list = QListWidget()
        red_bets_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(239, 83, 80, 0.03);
                border: 1px solid rgba(239, 83, 80, 0.15);
                border-radius: 8px;
                padding: 8px;
            }
            QListWidget::item {
                background: rgba(239, 83, 80, 0.12);
                color: #FFCDD2;
                border: 1px solid rgba(239, 83, 80, 0.25);
                border-radius: 6px;
                padding: 6px 12px;
                margin-bottom: 4px;
            }
            QListWidget::item:hover {
                background: rgba(239, 83, 80, 0.18);
            }
        """)
        
        green_bets_list = QListWidget()
        green_bets_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(102, 187, 106, 0.03);
                border: 1px solid rgba(102, 187, 106, 0.15);
                border-radius: 8px;
                padding: 8px;
            }
            QListWidget::item {
                background: rgba(102, 187, 106, 0.12);
                color: #C8E6C9;
                border: 1px solid rgba(102, 187, 106, 0.25);
                border-radius: 6px;
                padding: 6px 12px;
                margin-bottom: 4px;
            }
            QListWidget::item:hover {
                background: rgba(102, 187, 106, 0.18);
            }
        """)

        # 解析 bet_details
        import re
        has_bet = False
        if h.bet_details and h.bet_details != "无投注":
            items = [x.strip() for x in h.bet_details.split(",") if x.strip()]
            for item in items:
                match = re.match(r"([^(]+)\((红队|绿队)(\d+)分\)", item)
                if match:
                    has_bet = True
                    name = match.group(1).strip()
                    team = match.group(2)
                    amount = match.group(3)
                    
                    display_text = f"👤  {name}    [{amount}分]"
                    list_item = QListWidgetItem(display_text)
                    list_item.setFont(QFont("Microsoft YaHei UI", 11, QFont.Weight.Bold))
                    list_item.setSizeHint(QSize(0, 38))
                    
                    if team == "红队":
                        red_bets_list.addItem(list_item)
                    else:
                        green_bets_list.addItem(list_item)
                else:
                    # 备用，防格式匹配失败
                    list_item = QListWidgetItem(item)
                    list_item.setFont(QFont("Microsoft YaHei UI", 11, QFont.Weight.Bold))
                    list_item.setSizeHint(QSize(0, 38))
                    red_bets_list.addItem(list_item)

        if not has_bet:
            empty_item1 = QListWidgetItem("暂无投注人员")
            empty_item1.setForeground(QColor("#718096"))
            empty_item1.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            red_bets_list.addItem(empty_item1)

            empty_item2 = QListWidgetItem("暂无投注人员")
            empty_item2.setForeground(QColor("#718096"))
            empty_item2.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            green_bets_list.addItem(empty_item2)

        red_bets_box = QWidget()
        r_box_layout = QVBoxLayout(red_bets_box)
        r_box_layout.setContentsMargins(0,0,0,0)
        r_box_layout.addWidget(QLabel("🔴 投注红队："))
        r_box_layout.addWidget(red_bets_list)

        green_bets_box = QWidget()
        g_box_layout = QVBoxLayout(green_bets_box)
        g_box_layout.setContentsMargins(0,0,0,0)
        g_box_layout.addWidget(QLabel("🟢 投注绿队："))
        g_box_layout.addWidget(green_bets_list)

        bets_columns_layout.addWidget(red_bets_box)
        bets_columns_layout.addWidget(green_bets_box)
        
        bets_main_layout.addLayout(bets_columns_layout)
        layout.addWidget(bets_group)

        # 底部关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setFixedHeight(38)
        close_btn.setFont(QFont("Microsoft YaHei UI", 11, QFont.Weight.Bold))
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #3182CE;
                color: white;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2B6CB0;
            }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


# ────────────────────────────────────────────────────────────────────
# 赛事总结算弹窗
# ────────────────────────────────────────────────────────────────────

class TournamentSummaryDialog(QDialog):
    """
    赛事总结算弹窗

    @author hyq
    @version 2026-07-13
    """

    def __init__(
        self,
        tournament: Tournament,
        leaderboard: list[dict[str, Any]],
        parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.setWindowTitle("🏆 赛事总结算")
        self.setMinimumSize(520, 550)
        self.resize(520, 600)
        self.setStyleSheet(DARK_STYLE)
        self._build_ui(tournament, leaderboard)

    def _build_ui(self, tournament: Tournament, leaderboard: list[dict[str, Any]]) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title = QLabel("🏆 本届赛事总结算")
        title.setFont(QFont("Microsoft YaHei UI", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #FFD700; margin-bottom: 5px;")
        layout.addWidget(title)

        # 庄家盈亏
        banker_color = "#4CAF50" if tournament.banker_profit >= 0 else "#F44336"
        banker_sign = "+" if tournament.banker_profit >= 0 else ""
        banker_label = QLabel(
            f"💼 庄家总盈亏：{banker_sign}{tournament.banker_profit} 分"
        )
        banker_label.setFont(QFont("Microsoft YaHei UI", 15, QFont.Weight.Bold))
        banker_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banker_label.setStyleSheet(f"color: {banker_color}; margin-bottom: 10px;")
        layout.addWidget(banker_label)

        # 滚动区域 (包裹排行数据，自适应任意分辨率)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #3a3a5c; border-radius: 8px; background-color: #16213e; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(15, 15, 15, 15)

        # 龙虎榜数据渲染
        if leaderboard:
            # 赚分最多
            winners = [p for p in leaderboard if p.get("tournament_profit", 0) > 0]
            winners.sort(key=lambda x: x["tournament_profit"], reverse=True)
            
            if winners:
                winners_label = QLabel("🐉 龙榜 - 赚分最多")
                winners_label.setFont(QFont("Microsoft YaHei UI", 13, QFont.Weight.Bold))
                winners_label.setStyleSheet("color: #4CAF50; margin-top: 5px;")
                scroll_layout.addWidget(winners_label)

                for i, p in enumerate(winners[:5]):
                    medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i] if i < 5 else f"{i+1}."
                    lbl = QLabel(f"  {medal} {p['name']}    +{p['tournament_profit']} 分")
                    lbl.setFont(QFont("Microsoft YaHei UI", 12))
                    lbl.setStyleSheet("color: #81C784;")
                    scroll_layout.addWidget(lbl)

            # 亏分最多
            losers = [p for p in leaderboard if p.get("tournament_profit", 0) < 0]
            losers.sort(key=lambda x: x["tournament_profit"])
            
            if losers:
                losers_label = QLabel("🐯 虎榜 - 亏分最多")
                losers_label.setFont(QFont("Microsoft YaHei UI", 13, QFont.Weight.Bold))
                losers_label.setStyleSheet("color: #F44336; margin-top: 15px;")
                scroll_layout.addWidget(losers_label)

                for i, p in enumerate(losers[:5]):
                    medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i] if i < 5 else f"{i+1}."
                    lbl = QLabel(f"  {medal} {p['name']}    {p['tournament_profit']} 分")
                    lbl.setFont(QFont("Microsoft YaHei UI", 12))
                    lbl.setStyleSheet("color: #E57373;")
                    scroll_layout.addWidget(lbl)
                    
        else:
            no_data_label = QLabel("暂无本届赛事排行数据")
            no_data_label.setFont(QFont("Microsoft YaHei UI", 12))
            no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data_label.setStyleSheet("color: #888;")
            scroll_layout.addWidget(no_data_label)

        scroll_content.setLayout(scroll_layout)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # 关闭按钮
        close_btn = QPushButton("确认关闭")
        close_btn.setStyleSheet(
            "background-color: #0f3460; color: white; padding: 10px 40px; "
            "font-size: 14px; border-radius: 6px; font-weight: bold;"
        )
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)


# ────────────────────────────────────────────────────────────────────
# 添加成员弹窗
# ────────────────────────────────────────────────────────────────────

class AddMemberDialog(QDialog):
    """
    添加新成员弹窗

    @author hyq
    @version 2026-07-13
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("➕ 添加新成员")
        self.setFixedSize(350, 180)
        self.setStyleSheet(DARK_STYLE)

        layout = QFormLayout(self)
        layout.setSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入成员名字")
        self.name_input.setStyleSheet(
            "background-color: #16213e; border: 1px solid #3a3a5c; "
            "border-radius: 4px; padding: 8px; color: #e0e0e0; font-size: 14px;"
        )
        layout.addRow("成员名字:", self.name_input)

        self.score_input = QSpinBox()
        self.score_input.setRange(-9999, 9999)
        self.score_input.setValue(0)
        layout.addRow("初始积分:", self.score_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_values(self) -> tuple[str, int]:
        return self.name_input.text().strip(), self.score_input.value()


# ────────────────────────────────────────────────────────────────────
# 红绿灯指示器控件
# ────────────────────────────────────────────────────────────────────

class TrafficLight(QWidget):
    """
    红/绿灯圆形指示器

    @author hyq
    @version 2026-07-13
    """

    def __init__(self, color: TeamColor, size: int = 48, parent: QWidget | None = None):
        super().__init__(parent)
        self.light_color = color
        self.size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.light_color == TeamColor.RED:
            # 红灯：多层渐变效果
            # 外圈发光
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 60, 60, 40)))
            painter.drawEllipse(0, 0, self.size, self.size)
            # 主体
            painter.setBrush(QBrush(QColor(220, 40, 40)))
            margin = 4
            painter.drawEllipse(margin, margin, self.size - margin * 2, self.size - margin * 2)
            # 高光
            painter.setBrush(QBrush(QColor(255, 120, 120, 160)))
            painter.drawEllipse(
                self.size // 4, self.size // 6,
                self.size // 3, self.size // 4
            )
        else:
            # 绿灯
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(60, 220, 60, 40)))
            painter.drawEllipse(0, 0, self.size, self.size)
            painter.setBrush(QBrush(QColor(40, 180, 40)))
            margin = 4
            painter.drawEllipse(margin, margin, self.size - margin * 2, self.size - margin * 2)
            painter.setBrush(QBrush(QColor(120, 255, 120, 160)))
            painter.drawEllipse(
                self.size // 4, self.size // 6,
                self.size // 3, self.size // 4
            )

        painter.end()


# ────────────────────────────────────────────────────────────────────
# 主窗口
# ────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """
    泡泡堂家族比赛积分竞猜系统 - 主窗口

    @author hyq
    @version 2026-07-13
    """

    def __init__(self, repository: Repository):
        super().__init__()
        self.repo = repository
        self.current_tournament: Tournament | None = None
        self.current_round_number: int = 1
        self.members: list[Member] = []
        self.game_accounts: list[Any] = []
        # 内存中的下注信息映射: {member_name: bet_amount}
        self._blind_bets: dict[str, int] = {}
        
        # 活跃池缓存集合，记录本届赛事所有投注过的成员与上场过的选手
        self.active_members_this_tournament: set[str] = set()
        self.active_players_this_tournament: set[str] = set()

        self.setWindowTitle("🎮 泡泡堂家族比赛积分竞猜系统")
        self.setMinimumSize(1150, 750)
        self.resize(1200, 800)
        self.setStyleSheet(DARK_STYLE)

        self._build_ui()
        self._load_data()

    # ────────────── 界面构建 ──────────────

    def _build_ui(self) -> None:
        """构建整体界面布局"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)

        # 使用 QSplitter 上下分割
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 上半部分 - 当前比赛操作区
        top_widget = self._build_top_panel()
        splitter.addWidget(top_widget)

        # 下半部分 - 归档展示区
        bottom_widget = self._build_bottom_panel()
        splitter.addWidget(bottom_widget)

        # 默认比例 6:4
        splitter.setSizes([560, 380])
        main_layout.addWidget(splitter)

    def _build_top_panel(self) -> QWidget:
        """构建上半部分操作区"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(10)

        # 左栏 - 家族成员大池 & 参赛选手大池
        left_widget = self._build_pool_panel()
        layout.addWidget(left_widget, 25)

        # 中栏 - 红绿两队阵营
        center_panel = self._build_teams_panel()
        layout.addWidget(center_panel, 57)

        # 右栏 - 控制台
        right_panel = self._build_control_panel()
        layout.addWidget(right_panel, 18)

        return widget

    def _build_pool_panel(self) -> QWidget:
        """构建成员与选手双池面板"""
        panel_widget = QWidget()
        panel_layout = QVBoxLayout(panel_widget)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(10)

        # 1. 家族成员大池 GroupBox
        group_member = QGroupBox("🏠 家族成员大池 (投注用)")
        member_layout = QVBoxLayout(group_member)
        member_layout.setContentsMargins(6, 8, 6, 6)
        member_layout.setSpacing(6)

        hint_label = QLabel("💡 拖拽成员至红/绿队进行投注")
        hint_label.setStyleSheet("color: #888; font-size: 11px; margin-bottom: 2px;")
        member_layout.addWidget(hint_label)

        # 【新】引入 QTabWidget 叠放成员池与活跃池，空间瞬间释放！
        self.member_tabs = QTabWidget()
        self.member_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #2d2d44; border-radius: 4px; background-color: #111122; }
            QTabBar::tab { background: #1a1a2e; color: #a0aec0; padding: 6px 12px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #2d2d44; color: #FFD700; font-weight: bold; }
        """)

        # Tab 1: 全部成员
        tab_all_member = QWidget()
        all_member_layout = QVBoxLayout(tab_all_member)
        all_member_layout.setContentsMargins(4, 4, 4, 4)
        all_member_layout.setSpacing(4)

        self.pool_list = DragListWidget(pool_type="member")
        self.pool_list.setFont(QFont("Microsoft YaHei UI", 12))
        all_member_layout.addWidget(self.pool_list)

        self.input_add_member = QLineEdit()
        self.input_add_member.setPlaceholderText("🔍 输入姓名查询搜索，回车物理添加新成员")
        self.input_add_member.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a2e;
                border: 1px dashed #2E7D32;
                border-radius: 6px;
                color: #e2e8f0;
                padding: 6px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
                background-color: #16162a;
            }
        """)
        self.input_add_member.returnPressed.connect(self._on_quick_add_member)
        self.input_add_member.textChanged.connect(self._on_search_member)
        all_member_layout.addWidget(self.input_add_member)

        # Tab 2: 本届活跃成员
        tab_active_member = QWidget()
        active_member_layout = QVBoxLayout(tab_active_member)
        active_member_layout.setContentsMargins(4, 4, 4, 4)

        self.active_member_pool_list = DragListWidget(pool_type="member")
        self.active_member_pool_list.setFont(QFont("Microsoft YaHei UI", 12))
        active_member_layout.addWidget(self.active_member_pool_list)

        self.member_tabs.addTab(tab_all_member, "📁 全部成员")
        self.member_tabs.addTab(tab_active_member, "⭐ 本届活跃")
        member_layout.addWidget(self.member_tabs)

        panel_layout.addWidget(group_member, 55)

        # 2. 参赛选手池 GroupBox
        group_player = QGroupBox("🎮 参赛选手池 (当次比赛实际ID)")
        player_layout = QVBoxLayout(group_player)
        player_layout.setContentsMargins(6, 8, 6, 6)
        player_layout.setSpacing(6)

        hint_label2 = QLabel("💡 拖拽至红/绿选手列表")
        hint_label2.setStyleSheet("color: #888; font-size: 11px; margin-bottom: 2px;")
        player_layout.addWidget(hint_label2)

        # 【新】引入 QTabWidget 叠放选手池与活跃选手池
        self.player_tabs = QTabWidget()
        self.player_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #2d2d44; border-radius: 4px; background-color: #111122; }
            QTabBar::tab { background: #1a1a2e; color: #a0aec0; padding: 6px 12px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #2d2d44; color: #90CAF9; font-weight: bold; }
        """)

        # Tab 1: 全部选手
        tab_all_player = QWidget()
        all_player_layout = QVBoxLayout(tab_all_player)
        all_player_layout.setContentsMargins(4, 4, 4, 4)
        all_player_layout.setSpacing(4)

        self.player_pool_list = DragListWidget(pool_type="player")
        self.player_pool_list.setFont(QFont("Microsoft YaHei UI", 12))
        all_player_layout.addWidget(self.player_pool_list)

        self.input_add_player = QLineEdit()
        self.input_add_player.setPlaceholderText("🔍 输入账号查询搜索，回车物理添加新选手")
        self.input_add_player.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a2e;
                border: 1px dashed #1565C0;
                border-radius: 6px;
                color: #e2e8f0;
                padding: 6px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #1E88E5;
                background-color: #16162a;
            }
        """)
        self.input_add_player.returnPressed.connect(self._on_quick_add_player)
        self.input_add_player.textChanged.connect(self._on_search_player)
        all_player_layout.addWidget(self.input_add_player)

        # Tab 2: 本届活跃选手
        tab_active_player = QWidget()
        active_player_layout = QVBoxLayout(tab_active_player)
        active_player_layout.setContentsMargins(4, 4, 4, 4)

        self.active_player_pool_list = DragListWidget(pool_type="player")
        self.active_player_pool_list.setFont(QFont("Microsoft YaHei UI", 12))
        active_player_layout.addWidget(self.active_player_pool_list)

        self.player_tabs.addTab(tab_all_player, "📁 全部选手")
        self.player_tabs.addTab(tab_active_player, "⭐ 本届活跃")
        player_layout.addWidget(self.player_tabs)

        panel_layout.addWidget(group_player, 45)

        return panel_widget

    def _build_teams_panel(self) -> QWidget:
        """构建红绿两队阵营区域"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(10)

        # 红队阵营
        red_group = QGroupBox()
        red_group.setStyleSheet(
            "QGroupBox { border: 2px solid #c62828; border-radius: 8px; "
            "margin-top: 0px; padding-top: 8px; }"
        )
        red_layout = QVBoxLayout(red_group)
        red_layout.setSpacing(6)

        # 红队标题行（红灯 + 文字）
        red_header = QHBoxLayout()
        red_light = TrafficLight(TeamColor.RED, 42)
        red_header.addWidget(red_light)
        red_title = QLabel("红队 RED")
        red_title.setFont(QFont("Microsoft YaHei UI", 16, QFont.Weight.Bold))
        red_title.setStyleSheet("color: #EF5350;")
        red_header.addWidget(red_title)
        red_header.addStretch()
        red_layout.addLayout(red_header)

        # 红队选手列表
        red_player_label = QLabel("⚔️ 红队选手")
        red_player_label.setStyleSheet("color: #EF9A9A; font-size: 12px; font-weight: bold;")
        red_layout.addWidget(red_player_label)

        self.red_players_list = DropListWidget(TeamColor.RED, True, self)
        self.red_players_list.setStyleSheet(
            "QListWidget { border: 1px solid #c62828; background-color: #1a0a0a; }"
        )
        red_layout.addWidget(self.red_players_list, 1)

        # 红队投注列表
        red_bet_label = QLabel("💰 红队投注")
        red_bet_label.setStyleSheet("color: #EF9A9A; font-size: 12px; font-weight: bold;")
        red_layout.addWidget(red_bet_label)

        self.red_bettors_list = DropListWidget(TeamColor.RED, False, self)
        self.red_bettors_list.setStyleSheet(
            "QListWidget { border: 1px solid #c62828; background-color: #1a0a0a; }"
        )
        red_layout.addWidget(self.red_bettors_list, 2)

        layout.addWidget(red_group)

        # ── VS 分隔 ──
        vs_label = QLabel("⚡\nVS")
        vs_label.setFont(QFont("Microsoft YaHei UI", 18, QFont.Weight.Bold))
        vs_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vs_label.setStyleSheet("color: #FFD700; min-width: 40px;")
        layout.addWidget(vs_label)

        # 绿队阵营
        green_group = QGroupBox()
        green_group.setStyleSheet(
            "QGroupBox { border: 2px solid #2E7D32; border-radius: 8px; "
            "margin-top: 0px; padding-top: 8px; }"
        )
        green_layout = QVBoxLayout(green_group)
        green_layout.setSpacing(6)

        # 绿队标题行（绿灯 + 文字）
        green_header = QHBoxLayout()
        green_light = TrafficLight(TeamColor.GREEN, 42)
        green_header.addWidget(green_light)
        green_title = QLabel("绿队 GREEN")
        green_title.setFont(QFont("Microsoft YaHei UI", 16, QFont.Weight.Bold))
        green_title.setStyleSheet("color: #66BB6A;")
        green_header.addWidget(green_title)
        green_header.addStretch()
        green_layout.addLayout(green_header)

        # 绿队选手列表
        green_player_label = QLabel("⚔️ 绿队选手")
        green_player_label.setStyleSheet("color: #A5D6A7; font-size: 12px; font-weight: bold;")
        green_layout.addWidget(green_player_label)

        self.green_players_list = DropListWidget(TeamColor.GREEN, True, self)
        self.green_players_list.setStyleSheet(
            "QListWidget { border: 1px solid #2E7D32; background-color: #0a1a0a; }"
        )
        green_layout.addWidget(self.green_players_list, 1)

        # 绿队投注列表
        green_bet_label = QLabel("💰 绿队投注")
        green_bet_label.setStyleSheet("color: #A5D6A7; font-size: 12px; font-weight: bold;")
        green_layout.addWidget(green_bet_label)

        self.green_bettors_list = DropListWidget(TeamColor.GREEN, False, self)
        self.green_bettors_list.setStyleSheet(
            "QListWidget { border: 1px solid #2E7D32; background-color: #0a1a0a; }"
        )
        green_layout.addWidget(self.green_bettors_list, 2)

        layout.addWidget(green_group)

        return widget

    def _build_control_panel(self) -> QGroupBox:
        """构建右侧控制台"""
        group = QGroupBox("📊 比赛控制台")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 15, 10, 10)

        # 赛事状态面板 (卡片式，防止不同分辨率重叠)
        status_card = QFrame()
        status_card.setStyleSheet(
            "QFrame { background-color: #0f172a; border: 1px solid #334155; "
            "border-radius: 6px; padding: 4px; }"
            "QLabel { color: #f8fafc; font-weight: bold; border: none; background: transparent; }"
        )
        status_layout = QVBoxLayout(status_card)
        status_layout.setSpacing(4)
        status_layout.setContentsMargins(6, 6, 6, 6)

        self.lbl_tour_status = QLabel("🏆 赛事状态：未开始")
        self.lbl_tour_status.setFont(QFont("Microsoft YaHei UI", 11, QFont.Weight.Bold))
        self.lbl_tour_status.setStyleSheet("color: #fbbf24;")  # 亮黄色
        status_layout.addWidget(self.lbl_tour_status)

        self.lbl_round_info = QLabel("📋 轮次信息：-")
        self.lbl_round_info.setFont(QFont("Microsoft YaHei UI", 10))
        status_layout.addWidget(self.lbl_round_info)

        self.lbl_banker_profit = QLabel("💼 庄家累计盈亏：0 分")
        self.lbl_banker_profit.setFont(QFont("Microsoft YaHei UI", 10))
        self.lbl_banker_profit.setStyleSheet("color: #34d399;") # 亮绿色
        status_layout.addWidget(self.lbl_banker_profit)

        layout.addWidget(status_card)

        # 下注上限
        limit_layout = QHBoxLayout()
        limit_label = QLabel("💎 下注上限:")
        limit_label.setFont(QFont("Microsoft YaHei UI", 11))
        limit_layout.addWidget(limit_label)
        self.max_bet_spin = QSpinBox()
        self.max_bet_spin.setRange(5, 100)
        self.max_bet_spin.setSingleStep(5)
        self.max_bet_spin.setValue(20)
        self.max_bet_spin.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.Bold))
        limit_layout.addWidget(self.max_bet_spin)
        layout.addLayout(limit_layout)

        # 分隔线
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet("color: #334155;")
        layout.addWidget(line1)

        # 比分输入
        score_label = QLabel("📋 本轮比分录入 (先赢4局胜)")
        score_label.setFont(QFont("Microsoft YaHei UI", 11, QFont.Weight.Bold))
        layout.addWidget(score_label)

        score_layout = QHBoxLayout()
        # 红队比分
        red_score_wrapper = QVBoxLayout()
        self.red_score_indicator = TrafficLight(TeamColor.RED, 20)
        red_score_wrapper.addWidget(self.red_score_indicator, alignment=Qt.AlignmentFlag.AlignCenter)
        self.red_score_spin = QSpinBox()
        self.red_score_spin.setRange(0, 4)
        self.red_score_spin.setFont(QFont("Microsoft YaHei UI", 16, QFont.Weight.Bold))
        self.red_score_spin.setStyleSheet("color: #EF5350; min-width: 50px;")
        red_score_wrapper.addWidget(self.red_score_spin)
        score_layout.addLayout(red_score_wrapper)

        vs_small = QLabel(":")
        vs_small.setFont(QFont("Microsoft YaHei UI", 18, QFont.Weight.Bold))
        vs_small.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_layout.addWidget(vs_small)

        # 绿队比分
        green_score_wrapper = QVBoxLayout()
        self.green_score_indicator = TrafficLight(TeamColor.GREEN, 20)
        green_score_wrapper.addWidget(self.green_score_indicator, alignment=Qt.AlignmentFlag.AlignCenter)
        self.green_score_spin = QSpinBox()
        self.green_score_spin.setRange(0, 4)
        self.green_score_spin.setFont(QFont("Microsoft YaHei UI", 16, QFont.Weight.Bold))
        self.green_score_spin.setStyleSheet("color: #66BB6A; min-width: 50px;")
        green_score_wrapper.addWidget(self.green_score_spin)
        score_layout.addLayout(green_score_wrapper)

        layout.addLayout(score_layout)

        # 分隔线
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("color: #334155;")
        layout.addWidget(line2)

        # 按钮组：合并排版以节省空间
        # 1. 赛事管理并排
        tour_btn_layout = QHBoxLayout()
        self.btn_start_tournament = QPushButton("🏆 开始新赛事")
        self.btn_start_tournament.setStyleSheet(
            "background-color: #2E7D32; color: white; font-size: 12px; padding: 6px;"
        )
        self.btn_start_tournament.clicked.connect(self._on_start_tournament)
        tour_btn_layout.addWidget(self.btn_start_tournament)

        self.btn_end_tournament = QPushButton("🛑 结束本次赛事")
        self.btn_end_tournament.setStyleSheet(
            "background-color: #C62828; color: white; font-size: 12px; padding: 6px;"
        )
        self.btn_end_tournament.setEnabled(False)
        self.btn_end_tournament.clicked.connect(self._on_end_tournament)
        tour_btn_layout.addWidget(self.btn_end_tournament)
        layout.addLayout(tour_btn_layout)

        # 2. 结算与重置
        self.btn_settle = QPushButton("⚡ 一键结算本轮")
        self.btn_settle.setStyleSheet(
            "background-color: #1565C0; color: white; font-size: 14px; "
            "padding: 10px; font-weight: bold;"
        )
        self.btn_settle.setEnabled(False)
        self.btn_settle.clicked.connect(self._on_settle_round)
        layout.addWidget(self.btn_settle)

        # 重置与导出并排
        tool_btn_layout = QHBoxLayout()
        self.btn_reset_round = QPushButton("🔄 重置本轮")
        self.btn_reset_round.setStyleSheet(
            "background-color: #455A64; color: white; font-size: 12px; padding: 6px;"
        )
        self.btn_reset_round.clicked.connect(self._on_reset_round)
        tool_btn_layout.addWidget(self.btn_reset_round)

        self.btn_export = QPushButton("📥 导出 Excel")
        self.btn_export.setStyleSheet(
            "background-color: #0f3460; color: white; font-size: 12px; padding: 6px;"
        )
        self.btn_export.clicked.connect(self._on_export_excel)
        tool_btn_layout.addWidget(self.btn_export)
        layout.addLayout(tool_btn_layout)

        layout.addStretch()
        return group

    def _build_bottom_panel(self) -> QWidget:
        """构建下半部分归档展示区"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(10)

        # 左栏 - 往期比赛历史 (带提示和显式详情按钮)
        history_group = QGroupBox("📜 往期比赛历史 (双击单行或点击下方按钮查看详情)")
        history_layout = QVBoxLayout(history_group)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(9)
        self.history_table.setHorizontalHeaderLabels([
            "赛事ID", "轮次", "红队比分", "绿队比分",
            "获胜方", "红队选手", "绿队选手", "投注明细", "庄家盈亏"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setStyleSheet(
            "QTableWidget { alternate-background-color: #1a2a4e; }"
        )
        self.history_table.itemDoubleClicked.connect(self._on_history_item_double_clicked)
        history_layout.addWidget(self.history_table)

        # 显式的查看详情按钮，直观性大增！
        self.btn_view_detail = QPushButton("🔍 查看选中轮次详情 (大字大面板)")
        self.btn_view_detail.setFixedHeight(34)
        self.btn_view_detail.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
        self.btn_view_detail.setStyleSheet("""
            QPushButton {
                background-color: #2b3a60;
                color: #e2e8f0;
                border: 1px solid #3d4f7c;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #384d80;
            }
        """)
        self.btn_view_detail.clicked.connect(self._on_view_selected_history_detail)
        history_layout.addWidget(self.btn_view_detail)
        layout.addWidget(history_group, 55)

        # 右栏 - 天梯积分榜
        ladder_group = QGroupBox("🏅 家族天梯积分榜")
        ladder_layout = QVBoxLayout(ladder_group)

        # 切换标签页
        self.ladder_tabs = QTabWidget()
        self.ladder_tabs.currentChanged.connect(self._on_ladder_tab_changed)

        # 本届赛事盈亏榜
        self.tournament_ladder_table = QTableWidget()
        self.tournament_ladder_table.setColumnCount(3)
        self.tournament_ladder_table.setHorizontalHeaderLabels(["排名", "成员", "本届盈亏"])
        self.tournament_ladder_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.tournament_ladder_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tournament_ladder_table.setAlternatingRowColors(True)
        self.tournament_ladder_table.setStyleSheet(
            "QTableWidget { alternate-background-color: #1a2a4e; }"
        )
        self.ladder_tabs.addTab(self.tournament_ladder_table, "📈 本届赛事盈亏榜")

        # 历史累计总榜
        self.total_ladder_table = QTableWidget()
        self.total_ladder_table.setColumnCount(3)
        self.total_ladder_table.setHorizontalHeaderLabels(["排名", "成员", "累计积分"])
        self.total_ladder_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.total_ladder_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.total_ladder_table.setAlternatingRowColors(True)
        self.total_ladder_table.setStyleSheet(
            "QTableWidget { alternate-background-color: #1a2a4e; }"
        )
        self.ladder_tabs.addTab(self.total_ladder_table, "📊 历史累计总榜")

        ladder_layout.addWidget(self.ladder_tabs)
        layout.addWidget(ladder_group, 45)

        return widget

    # ────────────── 数据加载 ──────────────

    def _load_data(self) -> None:
        """加载初始数据"""
        self.members = self.repo.get_all_members()
        self.game_accounts = self.repo.get_all_game_accounts()
        self._refresh_pool()
        self._refresh_player_pool()
        self._refresh_history()
        self._refresh_total_ladder()
        self._check_ongoing_tournament()

    def _check_ongoing_tournament(self) -> None:
        """检查是否有进行中的赛事"""
        try:
            from src.database.db_manager import DBManager
            with self.repo.db_manager.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, status, banker_profit, start_time, end_time "
                    "FROM tournaments WHERE status = 'ongoing'"
                )
                row = cursor.fetchone()
                if row:
                    self.current_tournament = Tournament(
                        id=row.id,
                        status=TournamentStatus(row.status),
                        banker_profit=row.banker_profit,
                        start_time=row.start_time,
                        end_time=row.end_time
                    )
                    # 获取当前轮次号
                    cursor.execute(
                        "SELECT MAX(round_number) FROM rounds WHERE tournament_id = ?",
                        (self.current_tournament.id,)
                    )
                    max_round = cursor.fetchone()[0]
                    self.current_round_number = (max_round or 0) + 1
                    self._update_tournament_status()
                    self._refresh_tournament_ladder()
                    
                    # 从往期历史恢复本届赛事已活跃的成员和选手缓存
                    histories = self.repo.get_match_history()
                    for h in histories:
                        if h.tournament_id == self.current_tournament.id:
                            if h.red_players:
                                for p in [x.strip() for x in h.red_players.split(",") if x.strip()]:
                                    self.active_players_this_tournament.add(p)
                            if h.green_players:
                                for p in [x.strip() for x in h.green_players.split(",") if x.strip()]:
                                    self.active_players_this_tournament.add(p)
                            if h.bet_details and h.bet_details != "无投注":
                                import re
                                items = [x.strip() for x in h.bet_details.split(",") if x.strip()]
                                for item in items:
                                    match = re.match(r"([^(]+)\((红队|绿队)(\d+)分\)", item)
                                    if match:
                                        self.active_members_this_tournament.add(match.group(1).strip())
                    self._refresh_active_pools()
        except Exception:
            pass

    def _refresh_pool(self) -> None:
        """刷新成员大池"""
        self.pool_list.clear()
        self.members = self.repo.get_all_members()
        for member in self.members:
            if member.is_banker:
                continue  # 庄家不显示在大池中
            self._add_member_to_pool(member.name)

    def _add_member_to_pool(
        self,
        name: str,
        bet_amount: int = 0,
        score: int | None = None
    ) -> None:
        """向大池添加一个成员项"""
        # 如果该成员已经加入了红队或绿队投注列表，则大池里不显示（避免重复拖入）
        for list_widget in [self.red_bettors_list, self.green_bettors_list]:
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if item and item.data(Qt.ItemDataRole.UserRole) == name:
                    return

        display = f"👤 {name}  ×"
        item = QListWidgetItem(display)
        item.setData(Qt.ItemDataRole.UserRole, name)
        item.setData(Qt.ItemDataRole.UserRole + 1, bet_amount)
        font = QFont("Microsoft YaHei UI", 11)
        item.setFont(font)
        from PyQt6.QtGui import QFontMetrics
        metrics = QFontMetrics(font)
        width = metrics.horizontalAdvance(display) + 45
        item.setSizeHint(QSize(width, 32))
        self.pool_list.addItem(item)

    def _refresh_player_pool(self) -> None:
        """刷新选手池大池"""
        self.player_pool_list.clear()
        self.game_accounts = self.repo.get_all_game_accounts()
        for ga in self.game_accounts:
            self._add_player_to_pool(ga.nickname)

    def _add_player_to_pool(self, nickname: str) -> None:
        """向选手池大池添加一个账号项"""
        # 如果该账号已经加入了红队或绿队选手列表，则大池里不显示（避免重复拖入）
        for list_widget in [self.red_players_list, self.green_players_list]:
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if item and item.data(Qt.ItemDataRole.UserRole) == nickname:
                    return

        display = f"🎮 {nickname}  ×"
        item = QListWidgetItem(display)
        item.setData(Qt.ItemDataRole.UserRole, nickname)
        font = QFont("Microsoft YaHei UI", 11)
        item.setFont(font)
        from PyQt6.QtGui import QFontMetrics
        metrics = QFontMetrics(font)
        width = metrics.horizontalAdvance(display) + 45
        item.setSizeHint(QSize(width, 32))
        self.player_pool_list.addItem(item)

    def _refresh_active_pools(self) -> None:
        """刷新本届赛事的活跃池（当前投注成员/当前比赛选手）"""
        self.active_member_pool_list.clear()
        self.active_player_pool_list.clear()

        # 1. 活跃成员池（大池排他去重）
        for name in sorted(self.active_members_this_tournament):
            already_in_team = False
            for list_widget in [self.red_bettors_list, self.green_bettors_list]:
                for i in range(list_widget.count()):
                    item = list_widget.item(i)
                    if item and item.data(Qt.ItemDataRole.UserRole) == name:
                        already_in_team = True
                        break
            if already_in_team:
                continue

            display = f"👤 {name}"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, name)
            font = QFont("Microsoft YaHei UI", 11)
            item.setFont(font)
            from PyQt6.QtGui import QFontMetrics
            metrics = QFontMetrics(font)
            width = metrics.horizontalAdvance(display) + 45
            item.setSizeHint(QSize(width, 32))
            self.active_member_pool_list.addItem(item)

        # 2. 活跃选手池（选手去重）
        for nickname in sorted(self.active_players_this_tournament):
            already_in_team = False
            for list_widget in [self.red_players_list, self.green_players_list]:
                for i in range(list_widget.count()):
                    item = list_widget.item(i)
                    if item and item.data(Qt.ItemDataRole.UserRole) == nickname:
                        already_in_team = True
                        break
            if already_in_team:
                continue

            display = f"🎮 {nickname}"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, nickname)
            font = QFont("Microsoft YaHei UI", 11)
            item.setFont(font)
            from PyQt6.QtGui import QFontMetrics
            metrics = QFontMetrics(font)
            width = metrics.horizontalAdvance(display) + 45
            item.setSizeHint(QSize(width, 32))
            self.active_player_pool_list.addItem(item)

        # 刷新完成后，保持当前的过滤词状态
        self._on_search_member(self.input_add_member.text())
        self._on_search_player(self.input_add_player.text())

    def _on_search_member(self, text: str) -> None:
        """成员大池 & 活跃成员池的模糊查询过滤"""
        search_text = text.strip().lower()
        for i in range(self.pool_list.count()):
            item = self.pool_list.item(i)
            name = item.data(Qt.ItemDataRole.UserRole)
            if name:
                item.setHidden(search_text not in name.lower())

        for i in range(self.active_member_pool_list.count()):
            item = self.active_member_pool_list.item(i)
            name = item.data(Qt.ItemDataRole.UserRole)
            if name:
                item.setHidden(search_text not in name.lower())

    def _on_search_player(self, text: str) -> None:
        """选手大池 & 活跃选手池的模糊查询过滤"""
        search_text = text.strip().lower()
        for i in range(self.player_pool_list.count()):
            item = self.player_pool_list.item(i)
            name = item.data(Qt.ItemDataRole.UserRole)
            if name:
                item.setHidden(search_text not in name.lower())

        for i in range(self.active_player_pool_list.count()):
            item = self.active_player_pool_list.item(i)
            name = item.data(Qt.ItemDataRole.UserRole)
            if name:
                item.setHidden(search_text not in name.lower())

    def _refresh_history(self) -> None:
        """刷新往期比赛历史表格"""
        histories = self.repo.get_match_history()
        self.histories_data = histories
        self.history_table.setRowCount(len(histories))

        for row_idx, h in enumerate(histories):
            # 赛事ID
            self.history_table.setItem(row_idx, 0, QTableWidgetItem(str(h.tournament_id)))
            # 轮次
            self.history_table.setItem(row_idx, 1, QTableWidgetItem(f"第{h.round_number}轮"))
            # 红队比分
            red_item = QTableWidgetItem(str(h.red_score))
            red_item.setForeground(QColor("#EF5350"))
            red_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_table.setItem(row_idx, 2, red_item)
            # 绿队比分
            green_item = QTableWidgetItem(str(h.green_score))
            green_item.setForeground(QColor("#66BB6A"))
            green_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_table.setItem(row_idx, 3, green_item)
            # 获胜方
            winner_item = QTableWidgetItem(
                "🔴 红队" if h.winner == TeamColor.RED else "🟢 绿队"
            )
            winner_color = "#EF5350" if h.winner == TeamColor.RED else "#66BB6A"
            winner_item.setForeground(QColor(winner_color))
            winner_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_table.setItem(row_idx, 4, winner_item)
            # 红队选手
            self.history_table.setItem(row_idx, 5, QTableWidgetItem(h.red_players or "-"))
            # 绿队选手
            self.history_table.setItem(row_idx, 6, QTableWidgetItem(h.green_players or "-"))
            # 投注明细
            self.history_table.setItem(row_idx, 7, QTableWidgetItem(h.bet_details or "无投注"))
            # 庄家盈亏
            profit_item = QTableWidgetItem(
                f"+{h.banker_round_profit}" if h.banker_round_profit >= 0
                else str(h.banker_round_profit)
            )
            profit_color = "#4CAF50" if h.banker_round_profit >= 0 else "#F44336"
            profit_item.setForeground(QColor(profit_color))
            profit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_table.setItem(row_idx, 8, profit_item)

    def _on_history_item_double_clicked(self, item: QTableWidgetItem) -> None:
        """双击历史记录列表某一行，弹出结构化对局详情"""
        row = item.row()
        if hasattr(self, "histories_data") and row < len(self.histories_data):
            h = self.histories_data[row]
            dialog = MatchHistoryDetailsDialog(h, self)
            dialog.exec()

    def _on_view_selected_history_detail(self) -> None:
        """查看当前选中行的详情（点下部按钮触发）"""
        selected_items = self.history_table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "💡 提示", "请先在往期比赛历史列表中点击选择一行！")
            return
        row = selected_items[0].row()
        if hasattr(self, "histories_data") and row < len(self.histories_data):
            h = self.histories_data[row]
            dialog = MatchHistoryDetailsDialog(h, self)
            dialog.exec()

    def _refresh_total_ladder(self) -> None:
        """刷新历史累计总榜"""
        members = self.repo.get_all_members()
        # 按积分降序排列
        sorted_members = sorted(members, key=lambda m: m.historical_score, reverse=True)

        self.total_ladder_table.setRowCount(len(sorted_members))
        for row_idx, m in enumerate(sorted_members):
            # 排名
            rank_text = ["🥇", "🥈", "🥉"][row_idx] if row_idx < 3 else str(row_idx + 1)
            rank_item = QTableWidgetItem(rank_text)
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.total_ladder_table.setItem(row_idx, 0, rank_item)
            # 成员名
            name_item = QTableWidgetItem(m.name)
            if m.is_banker:
                name_item.setText(f"👑 {m.name}")
            self.total_ladder_table.setItem(row_idx, 1, name_item)
            # 积分
            score_text = f"+{m.historical_score}" if m.historical_score > 0 else str(m.historical_score)
            score_item = QTableWidgetItem(score_text)
            score_color = "#4CAF50" if m.historical_score > 0 else (
                "#F44336" if m.historical_score < 0 else "#888"
            )
            score_item.setForeground(QColor(score_color))
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            score_item.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.Bold))
            self.total_ladder_table.setItem(row_idx, 2, score_item)

    def _refresh_tournament_ladder(self) -> None:
        """刷新本届赛事盈亏榜"""
        if self.current_tournament is None:
            self.tournament_ladder_table.setRowCount(0)
            return

        leaderboard = self.repo.get_tournament_leaderboard(self.current_tournament.id)
        
        # 加上庄家置顶行，总行数 +1
        self.tournament_ladder_table.setRowCount(len(leaderboard) + 1)
        
        # 1. 庄家置顶高亮行
        rank_item = QTableWidgetItem("👑")
        rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tournament_ladder_table.setItem(0, 0, rank_item)
        
        name_item = QTableWidgetItem("主持人 (庄家)")
        name_item.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.Bold))
        name_item.setForeground(QColor("#FFD700"))
        self.tournament_ladder_table.setItem(0, 1, name_item)
        
        banker_profit = self.current_tournament.banker_profit
        profit_text = f"+{banker_profit}" if banker_profit > 0 else str(banker_profit)
        profit_item = QTableWidgetItem(profit_text)
        profit_color = "#4CAF50" if banker_profit > 0 else (
            "#F44336" if banker_profit < 0 else "#888"
        )
        profit_item.setForeground(QColor(profit_color))
        profit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        profit_item.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.Bold))
        self.tournament_ladder_table.setItem(0, 2, profit_item)
        
        # 2. 其他成员行 (由于庄家置顶，索引整体顺延 1)
        for idx, entry in enumerate(leaderboard):
            row_idx = idx + 1
            rank_item_member = QTableWidgetItem(str(row_idx))
            rank_item_member.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tournament_ladder_table.setItem(row_idx, 0, rank_item_member)

            name_item_member = QTableWidgetItem(entry["name"])
            self.tournament_ladder_table.setItem(row_idx, 1, name_item_member)

            profit = entry.get("tournament_profit", 0)
            profit_text = f"+{profit}" if profit > 0 else str(profit)
            profit_item_member = QTableWidgetItem(profit_text)
            profit_color_member = "#4CAF50" if profit > 0 else (
                "#F44336" if profit < 0 else "#888"
            )
            profit_item_member.setForeground(QColor(profit_color_member))
            profit_item_member.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            profit_item_member.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.Bold))
            self.tournament_ladder_table.setItem(row_idx, 2, profit_item_member)

    def _update_tournament_status(self) -> None:
        """更新赛事状态标签"""
        if self.current_tournament is None:
            self.lbl_tour_status.setText("🏆 赛事状态：未开始")
            self.lbl_round_info.setText("📋 轮次信息：-")
            self.lbl_banker_profit.setText("💼 庄家累计盈亏：0 分")
            self.btn_settle.setEnabled(False)
            self.btn_end_tournament.setEnabled(False)
            self.btn_start_tournament.setEnabled(True)
        else:
            self.lbl_tour_status.setText(f"🏆 赛事 #{self.current_tournament.id} 进行中")
            self.lbl_round_info.setText(f"📋 当前轮次：第 {self.current_round_number} 轮")
            self.lbl_banker_profit.setText(f"💼 庄家累计盈亏：{self.current_tournament.banker_profit:+d} 分")
            self.btn_settle.setEnabled(True)
            self.btn_end_tournament.setEnabled(True)
            self.btn_start_tournament.setEnabled(False)

    # ────────────── 辅助方法 ──────────────

    def _get_bettor_list(self, team: TeamColor) -> DropListWidget:
        """根据队伍颜色获取对应的投注列表"""
        return self.red_bettors_list if team == TeamColor.RED else self.green_bettors_list

    def _collect_team_names(self, list_widget: QListWidget) -> list[str]:
        """收集列表中所有成员名字"""
        names = []
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item:
                name = item.data(Qt.ItemDataRole.UserRole)
                if name:
                    names.append(name)
        return names

    def _collect_bets_from_list(
        self,
        list_widget: QListWidget,
        team: TeamColor,
        is_player_list: bool = False
    ) -> list[dict]:
        """从列表收集投注信息"""
        bets = []
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item is None:
                continue
            name = item.data(Qt.ItemDataRole.UserRole)
            amount = item.data(Qt.ItemDataRole.UserRole + 1) or 0
            if amount > 0:
                # 查找成员ID
                member_id = None
                for m in self.members:
                    if m.name == name:
                        member_id = m.id
                        break
                if member_id:
                    bets.append({
                        "member_id": member_id,
                        "member_name": name,
                        "bet_amount": amount,
                        "prediction": team,
                        "profit_loss": 0,
                        "is_player": is_player_list or bool(item.data(Qt.ItemDataRole.UserRole + 2))
                    })
        return bets

    # ────────────── 事件处理 ──────────────



    def _on_add_member(self) -> None:
        """添加新成员"""
        dialog = AddMemberDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, score = dialog.get_values()
            if not name:
                QMessageBox.warning(self, "⚠️ 错误", "成员名字不能为空！")
                return
            try:
                self.repo.add_member(name, score)
                self.members = self.repo.get_all_members()
                self._refresh_pool()
                self._refresh_total_ladder()
                QMessageBox.information(self, "✅ 成功", f"成员「{name}」已添加！")
            except ValueError as e:
                QMessageBox.warning(self, "⚠️ 错误", str(e))

    def _on_add_game_account(self) -> None:
        """添加新选手游戏ID"""
        name, ok = QInputDialog.getText(
            self, "➕ 添加新选手游戏ID",
            "请输入选手游戏账号名称:"
        )
        if ok:
            name = name.strip()
            if not name:
                QMessageBox.warning(self, "⚠️ 错误", "账号名称不能为空！")
                return
            try:
                self.repo.add_game_account(name)
                self.game_accounts = self.repo.get_all_game_accounts()
                self._refresh_player_pool()
                QMessageBox.information(self, "✅ 成功", f"游戏账号「{name}」已添加！")
            except ValueError as e:
                QMessageBox.warning(self, "⚠️ 错误", str(e))

    def _on_quick_add_member(self) -> None:
        """回车快捷添加新成员"""
        name = self.input_add_member.text().strip()
        if not name:
            return
        try:
            self.repo.add_member(name, 0)
            self.members = self.repo.get_all_members()
            self._refresh_pool()
            self._refresh_total_ladder()
            self.input_add_member.clear()
        except ValueError as e:
            QMessageBox.warning(self, "⚠️ 错误", str(e))

    def _on_quick_add_player(self) -> None:
        """回车快捷添加新选手账号"""
        nickname = self.input_add_player.text().strip()
        if not nickname:
            return
        try:
            self.repo.add_game_account(nickname)
            self.game_accounts = self.repo.get_all_game_accounts()
            self._refresh_player_pool()
            self.input_add_player.clear()
        except Exception as e:
            QMessageBox.warning(self, "⚠️ 错误", str(e))

    def _delete_pool_item(self, pool_type: str, name: str) -> None:
        """彻底从数据库物理删除某项成员或游戏账号"""
        try:
            # 1. 事务只执行删除操作，确保 write 提交后才读取，防止内部查询隔离读到旧值
            with self.repo.db_manager.connection(write=True) as conn:
                if pool_type == "member":
                    conn.execute("DELETE FROM members WHERE name = ?", (name,))
                else:
                    conn.execute("DELETE FROM game_accounts WHERE nickname = ?", (name,))
            
            # 2. 事务完全提交后，再读取数据库最新成员/账号列表并刷新界面，解决需点击两次才消失的问题
            if pool_type == "member":
                self.members = self.repo.get_all_members()
                self._refresh_pool()
                self._refresh_total_ladder()
            else:
                self.game_accounts = self.repo.get_all_game_accounts()
                self._refresh_player_pool()
        except Exception as e:
            QMessageBox.critical(self, "❌ 删除失败", f"数据库删除时出错：\n{e}")

    def _on_start_tournament(self) -> None:
        """开始新赛事"""
        reply = QMessageBox.question(
            self, "🏆 开始新赛事",
            "确认要开始一场新赛事吗？\n所有人的本届赛事盈亏将从 0 开始计算。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self.current_tournament = self.repo.start_tournament()
            self.current_round_number = 1
            self._blind_bets.clear()
            self.active_members_this_tournament.clear()
            self.active_players_this_tournament.clear()
            self._refresh_active_pools()
            self._update_tournament_status()
            self._refresh_tournament_ladder()
            self._on_reset_round()
            QMessageBox.information(
                self, "✅ 赛事已开始",
                f"赛事 #{self.current_tournament.id} 已开始！\n请组织第 1 轮比赛。"
            )
        except ValueError as e:
            QMessageBox.warning(self, "⚠️ 错误", str(e))

    def _on_end_tournament(self) -> None:
        """结束本次赛事"""
        if self.current_tournament is None:
            return

        reply = QMessageBox.question(
            self, "🛑 结束赛事",
            f"确认要结束赛事 #{self.current_tournament.id} 吗？\n结束后将展示总结算报告。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            tournament_id = self.current_tournament.id
            leaderboard = self.repo.get_tournament_leaderboard(tournament_id)
            ended_tournament = self.repo.end_tournament(tournament_id)

            # 弹出总结算弹窗
            dialog = TournamentSummaryDialog(ended_tournament, leaderboard, self)
            dialog.exec()

            self.current_tournament = None
            self.current_round_number = 1
            self._blind_bets.clear()
            self.active_members_this_tournament.clear()
            self.active_players_this_tournament.clear()
            self._refresh_active_pools()
            self._update_tournament_status()
            self._on_reset_round()
            self._refresh_history()
            self._refresh_total_ladder()
            self._refresh_tournament_ladder()

        except ValueError as e:
            QMessageBox.warning(self, "⚠️ 错误", str(e))

    def _on_settle_round(self) -> None:
        """一键结算本轮"""
        if self.current_tournament is None:
            QMessageBox.warning(self, "⚠️ 提示", "请先开始赛事！")
            return

        red_score = self.red_score_spin.value()
        green_score = self.green_score_spin.value()

        # 1. 验证比分
        try:
            winner = validate_match_score(red_score, green_score)
        except MatchResultValidationError as e:
            QMessageBox.warning(self, "⚠️ 比分无效", str(e))
            return

        # 2. 收集选手名单
        red_player_names = self._collect_team_names(self.red_players_list)
        green_player_names = self._collect_team_names(self.green_players_list)

        # 3. 收集投注信息
        all_bets: list[dict] = []
        # 从红队投注列表收集
        all_bets.extend(self._collect_bets_from_list(self.red_bettors_list, TeamColor.RED))
        # 从绿队投注列表收集
        all_bets.extend(self._collect_bets_from_list(self.green_bettors_list, TeamColor.GREEN))

        # 3.5 校验队伍绑定关系是否合法
        red_bettor_names = self._collect_team_names(self.red_bettors_list)
        green_bettor_names = self._collect_team_names(self.green_bettors_list)
        try:
            validate_team_bindings(
                red_player_names,
                green_player_names,
                red_bettor_names,
                green_bettor_names
            )
        except TeamBindingValidationError as e:
            QMessageBox.warning(self, "⚠️ 队伍绑定无效", str(e))
            return

        if not all_bets:
            reply = QMessageBox.question(
                self, "⚠️ 无投注",
                "本轮没有任何投注记录，确认要直接录入比分结果吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # 4. 结算
        settlement_result = calculate_settlement(all_bets, winner)
        settlements = settlement_result["settlements"]
        banker_round_profit = settlement_result["banker_round_profit"]

        # 4.5 拼接投注详情字符串，格式如 "棉花(红10分), 小黑(绿10分)"
        bet_detail_list = []
        for b in all_bets:
            pred_text = "红队" if b["prediction"] == TeamColor.RED else "绿队"
            bet_detail_list.append(f"{b['member_name']}({pred_text}{b['bet_amount']}分)")
        bet_details_str = ", ".join(bet_detail_list) if bet_detail_list else "无投注"

        # 5. 构建 Round 数据
        round_data = Round(
            tournament_id=self.current_tournament.id,
            round_number=self.current_round_number,
            red_score=red_score,
            green_score=green_score,
            winner=winner,
            banker_round_profit=banker_round_profit,
            red_players=", ".join(red_player_names),
            green_players=", ".join(green_player_names),
            bet_details=bet_details_str
        )

        # 6. 构建 Bet 数据
        bet_objects: list[Bet] = []
        for s in settlements:
            bet_objects.append(Bet(
                round_id=0,  # 由 repository 自动填充
                member_id=s["member_id"],
                bet_amount=s["bet_amount"],
                prediction=s["prediction"],
                profit_loss=s["profit_loss"],
                is_player=s.get("is_player", False)
            ))

        # 7. 保存到数据库
        try:
            self.repo.save_round_settlement(round_data, bet_objects)
        except Exception as e:
            QMessageBox.critical(self, "❌ 结算失败", f"数据库事务失败：\n{e}")
            return

        # 8. 构建结算结果摘要
        winner_text = "🔴 红队" if winner == TeamColor.RED else "🟢 绿队"
        summary_lines = [
            f"✅ 第 {self.current_round_number} 轮结算完成！",
            f"比分：红 {red_score} : {green_score} 绿",
            f"获胜方：{winner_text}",
            f"庄家本轮盈亏：{banker_round_profit:+d} 分",
            "",
        ]
        for s in settlements:
            sign = "+" if s["profit_loss"] > 0 else ""
            summary_lines.append(
                f"  {s['member_name']}: 押注{s['bet_amount']}分 → {sign}{s['profit_loss']}分"
            )

        QMessageBox.information(self, "⚡ 结算完成", "\n".join(summary_lines))

        # 9. 更新状态
        self.current_round_number += 1
        # 重新读取赛事数据以更新庄家累计盈亏
        with self.repo.db_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, status, banker_profit, start_time, end_time "
                "FROM tournaments WHERE id = ?",
                (self.current_tournament.id,)
            )
            row = cursor.fetchone()
            if row:
                self.current_tournament = Tournament(
                    id=row.id,
                    status=TournamentStatus(row.status),
                    banker_profit=row.banker_profit,
                    start_time=row.start_time,
                    end_time=row.end_time
                )

        self._blind_bets.clear()
        self._update_tournament_status()
        self._on_reset_round()
        self._refresh_history()
        self._refresh_total_ladder()
        self._refresh_tournament_ladder()
        # 重新加载成员数据（积分已更新）
        self.members = self.repo.get_all_members()
        self._refresh_pool()

    def _on_reset_round(self) -> None:
        """重置本轮"""
        # 将红/绿队中的成员退回大池
        for list_widget in [
            self.red_players_list, self.red_bettors_list,
            self.green_players_list, self.green_bettors_list
        ]:
            list_widget.clear()

        # 重置比分
        self.red_score_spin.setValue(0)
        self.green_score_spin.setValue(0)

        # 重新加载大池和选手大池
        self._refresh_pool()
        self._refresh_player_pool()
        self._refresh_active_pools()

    def _on_export_excel(self) -> None:
        """导出全部结果到 Excel"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出 Excel", "泡泡堂积分记录.xlsx",
            "Excel 文件 (*.xlsx)"
        )
        if not file_path:
            return

        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill

            wb = openpyxl.Workbook()

            # Sheet 1: 比赛历史
            ws1 = wb.active
            ws1.title = "比赛历史"
            headers1 = ["赛事ID", "轮次", "红队比分", "绿队比分", "获胜方", "红队选手", "绿队选手", "投注明细", "庄家盈亏"]
            ws1.append(headers1)

            # 设置表头样式
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="0F3460", end_color="0F3460", fill_type="solid")
            for col_idx, cell in enumerate(ws1[1], 1):
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")

            histories = self.repo.get_match_history()
            for h in histories:
                ws1.append([
                    h.tournament_id,
                    f"第{h.round_number}轮",
                    h.red_score,
                    h.green_score,
                    "红队" if h.winner == TeamColor.RED else "绿队",
                    h.red_players or "-",
                    h.green_players or "-",
                    h.bet_details or "无投注",
                    h.banker_round_profit
                ])

            # 自动调整列宽
            for col in ws1.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws1.column_dimensions[col[0].column_letter].width = max(max_len + 4, 10)

            # Sheet 2: 成员积分
            ws2 = wb.create_sheet("成员积分")
            headers2 = ["排名", "成员名", "历史累计积分", "是否庄家"]
            ws2.append(headers2)
            for cell in ws2[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")

            members = self.repo.get_all_members()
            sorted_members = sorted(members, key=lambda m: m.historical_score, reverse=True)
            for idx, m in enumerate(sorted_members, 1):
                ws2.append([
                    idx, m.name, m.historical_score,
                    "是" if m.is_banker else "否"
                ])

            for col in ws2.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws2.column_dimensions[col[0].column_letter].width = max(max_len + 4, 10)

            # Sheet 3: 本届赛事盈亏榜（仅统计今天真正参与过且产生盈亏的活跃选手和成员）
            t_id = None
            if self.current_tournament:
                t_id = self.current_tournament.id
            else:
                with self.repo.db_manager.connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT MAX(id) FROM tournaments")
                    row = cursor.fetchone()
                    if row and row[0] is not None:
                        t_id = row[0]

            if t_id:
                ws3 = wb.create_sheet("本届赛事盈亏榜")
                headers3 = ["赛事ID", "排名", "成员/选手", "本届盈亏", "身份类型"]
                ws3.append(headers3)
                for cell in ws3[1]:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = Alignment(horizontal="center")

                # 1. 物理从数据库直接查出庄家的名字与本届赛事庄家累计盈亏
                banker_name = "主持人(庄家)"
                banker_profit = 0
                with self.repo.db_manager.connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM members WHERE is_banker = 1 LIMIT 1")
                    row_name = cursor.fetchone()
                    if row_name:
                        banker_name = row_name[0]
                    
                    cursor.execute("SELECT banker_profit FROM tournaments WHERE id = ?", (t_id,))
                    row_profit = cursor.fetchone()
                    if row_profit and row_profit[0] is not None:
                        banker_profit = row_profit[0]

                # 2. 写入置顶第一行的庄家数据
                ws3.append([
                    t_id,
                    "★",
                    banker_name,
                    banker_profit,
                    "庄家(主持人)"
                ])

                # 3. 提取其他普通下注与参赛成员（过滤掉盈亏为 0 的今天未参与的普通人）
                raw_ladder = self.repo.get_tournament_leaderboard(t_id)
                others = []
                for p in raw_ladder:
                    profit = p.get("tournament_profit", 0)
                    # 排除今天没有参与的非活跃人员，且因为庄家上面已物理写入，这里遇到庄家名字也不重复录入
                    if profit != 0 and p.get("name") != banker_name:
                        others.append(p)

                # 按本届盈亏降序排序普通人员并写入，从排名1开始顺延
                sorted_others = sorted(others, key=lambda x: x.get("tournament_profit", 0), reverse=True)
                for idx, p in enumerate(sorted_others, 1):
                    ws3.append([
                        t_id,
                        idx,
                        p.get("name"),
                        p.get("tournament_profit", 0),
                        "活跃成员/选手"
                    ])

                for col in ws3.columns:
                    max_len = max(len(str(cell.value or "")) for cell in col)
                    ws3.column_dimensions[col[0].column_letter].width = max(max_len + 4, 10)

            wb.save(file_path)
            QMessageBox.information(self, "✅ 导出成功", f"数据已导出到：\n{file_path}")

        except ImportError:
            QMessageBox.critical(
                self, "❌ 缺少依赖",
                "请先安装 openpyxl：\npip install openpyxl"
            )
        except Exception as e:
            QMessageBox.critical(self, "❌ 导出失败", f"导出过程中发生错误：\n{e}")

    def _on_ladder_tab_changed(self, index: int) -> None:
        """天梯榜标签切换"""
        if index == 0:
            self._refresh_tournament_ladder()
        else:
            self._refresh_total_ladder()
