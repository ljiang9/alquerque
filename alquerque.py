"""Alquerque（阿爾克棋）:古老的跳吃棋，西洋跳棋的前身。

规则（常见标准）:
- 5x5 点阵棋盘，横竖线全连；斜线只画在 (行+列) 为偶数的格子里
  （形成贯穿棋盘的长斜线）。
- 双方各 12 子。黑方占第 0、1 行全部，外加 (2,0)、(2,1)；
  白方占第 3、4 行全部，外加 (2,3)、(2,4)；(2,2) 空。白方先手。
- 走子：沿线走一格到空点。
- 吃子：跳过相邻敌子落到其后空点（必须沿线）；**有吃必吃**，
  且多条吃子路线时必须选吃子数最多的路线；同一子可连跳。
- 胜负：吃光对方，或对方无棋可走，即胜。
"""

import argparse
import random
import sys

SIZE = 5
EMPTY, BLACK, WHITE = 0, 1, 2
DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
MAX_HALF_MOVES = 400


def other(player):
    return WHITE if player == BLACK else BLACK


def in_bounds(r, c):
    return 0 <= r < SIZE and 0 <= c < SIZE


def diag_allowed(r, c, dr, dc):
    """从 (r,c) 沿对角方向 (dr,dc) 是否有线。"""
    if abs(dr) != 1 or abs(dc) != 1:
        return True
    sr, sc = min(r, r + dr), min(c, c + dc)
    return (sr + sc) % 2 == 0


def neighbors(r, c):
    for dr, dc in DIRS:
        nr, nc = r + dr, c + dc
        if in_bounds(nr, nc) and diag_allowed(r, c, dr, dc):
            yield dr, dc, nr, nc


class Alquerque:
    def __init__(self):
        self.board = [[EMPTY] * SIZE for _ in range(SIZE)]
        for c in range(SIZE):
            self.board[0][c] = BLACK
            self.board[1][c] = BLACK
            self.board[3][c] = WHITE
            self.board[4][c] = WHITE
        self.board[2][0] = BLACK
        self.board[2][1] = BLACK
        self.board[2][3] = WHITE
        self.board[2][4] = WHITE
        # (2,2) 留空
        self.turn = WHITE
        self.half_moves = 0

    def count(self, player):
        return sum(row.count(player) for row in self.board)

    # ---- 走法生成 ----

    def _captures_from(self, r, c, board, path, captured):
        """回溯枚举从 (r,c) 出发的所有吃子路径。返回 (路径, 吃子集合) 列表。"""
        player = board[r][c]
        foe = other(player)
        results = []
        for dr, dc, mr, mc in neighbors(r, c):
            lr, lc = r + 2 * dr, c + 2 * dc
            if not in_bounds(lr, lc):
                continue
            # 跳跃后半段的对角线也必须有线（长斜线连续，首段合法则后段自动合法）
            if board[mr][mc] == foe and board[lr][lc] == EMPTY and (mr, mc) not in captured:
                nb = [row[:] for row in board]
                nb[r][c] = EMPTY
                nb[mr][mc] = EMPTY
                nb[lr][lc] = player
                ncap = captured | {(mr, mc)}
                sub = self._captures_from(lr, lc, nb, path + [(lr, lc)], ncap)
                if sub:
                    results.extend(sub)
                else:
                    results.append((path + [(lr, lc)], ncap))
        return results

    def captures(self, player):
        """该方所有吃子路线（路径点列表）。"""
        all_caps = []
        for r in range(SIZE):
            for c in range(SIZE):
                if self.board[r][c] == player:
                    for path, _ in self._captures_from(r, c, self.board, [(r, c)], set()):
                        all_caps.append(path)
        return all_caps

    def steps(self, player):
        moves = []
        for r in range(SIZE):
            for c in range(SIZE):
                if self.board[r][c] == player:
                    for _, _, nr, nc in neighbors(r, c):
                        if self.board[nr][nc] == EMPTY:
                            moves.append([(r, c), (nr, nc)])
        return moves

    def legal_moves(self, player):
        """有吃必吃；多条路线取吃子数最多者。"""
        caps = self.captures(player)
        if caps:
            best = max(len(p) for p in caps)
            return [p for p in caps if len(p) == best]
        return self.steps(player)

    # ---- 执行 ----

    def apply_path(self, player, path):
        """执行一条合法路径（吃子或走子）。非法抛 ValueError。"""
        legal = self.legal_moves(player)
        if path not in legal:
            raise ValueError(f"非法走法: {path}")
        r, c = path[0]
        self.board[r][c] = EMPTY
        for (nr, nc) in path[1:]:
            if max(abs(nr - r), abs(nc - c)) == 2:  # 跳吃（横/竖/斜）
                self.board[(r + nr) // 2][(c + nc) // 2] = EMPTY
            r, c = nr, nc
        self.board[r][c] = player
        self.turn = other(player)
        self.half_moves += 1

    def winner(self):
        """返回 BLACK/WHITE/0(和棋)/None(未结束)。"""
        b, w = self.count(BLACK), self.count(WHITE)
        if b == 0:
            return WHITE
        if w == 0:
            return BLACK
        if not self.legal_moves(self.turn):
            return other(self.turn)
        if self.half_moves >= MAX_HALF_MOVES:
            return 0
        return None

    # ---- 渲染 ----

    def render(self):
        glyph = {EMPTY: "·", BLACK: "●", WHITE: "○"}
        lines = ["   " + " ".join("abcde")]
        for r in range(SIZE):
            lines.append(f"{5 - r}  " + " ".join(glyph[self.board[r][c]] for c in range(SIZE)))
        return "\n".join(lines)


# ---- AI ----

def evaluate(board, player):
    foe = other(player)
    mine = sum(row.count(player) for row in board)
    theirs = sum(row.count(foe) for row in board)
    adv = 0
    for r in range(SIZE):
        for c in range(SIZE):
            if board[r][c] == player:
                adv += r if player == BLACK else (SIZE - 1 - r)
            elif board[r][c] == foe:
                adv -= r if foe == BLACK else (SIZE - 1 - r)
    return (mine - theirs) * 100 + adv


def ai_move(game, player, rng):
    moves = game.legal_moves(player)
    if not moves:
        return None
    if len(moves[0]) > 2 or any(abs(m[1][0] - m[0][0]) == 2 for m in moves):
        # 吃子回合：规则已限定为最多吃子路线，随机选一条
        return rng.choice(moves)
    best, best_moves = None, []
    for m in moves:
        g2 = Alquerque.__new__(Alquerque)
        g2.board = [row[:] for row in game.board]
        (r, c), (nr, nc) = m
        g2.board[r][c] = EMPTY
        g2.board[nr][nc] = player
        s = evaluate(g2.board, player) + rng.random()
        if best is None or s > best:
            best, best_moves = s, [m]
        elif s == best:
            best_moves.append(m)
    return rng.choice(best_moves)


def parse_coord(tok):
    tok = tok.strip().lower()
    if len(tok) == 2 and tok[0] in "abcde" and tok[1] in "12345":
        c = "abcde".index(tok[0])
        r = 5 - int(tok[1])
        return (r, c)
    raise ValueError(f"坐标格式错误: {tok}（示例: c3）")


def play_auto(games, seed, verbose):
    rng = random.Random(seed)
    bw = ww = dr = 0
    for i in range(games):
        g = Alquerque()
        while True:
            w = g.winner()
            if w is not None:
                break
            m = ai_move(g, g.turn, rng)
            if m is None:
                break
            g.apply_path(g.turn, m)
        w = g.winner()
        if w == BLACK:
            bw += 1
            res = "黑胜"
        elif w == WHITE:
            ww += 1
            res = "白胜"
        else:
            dr += 1
            res = "和棋"
        if verbose:
            print(f"第 {i + 1}/{games} 局: {res}（{g.half_moves} 半回合，黑剩 {g.count(BLACK)} / 白剩 {g.count(WHITE)}）")
    print(f"总计：黑胜 {bw}，白胜 {ww}，和棋 {dr}")


def play_interactive(seed):
    rng = random.Random(seed)
    g = Alquerque()
    human = WHITE
    print("你是白方 ○（先手），输入如 c3-d4，多跳如 c3-e5-c5，q 退出。")
    while True:
        print()
        print(g.render())
        w = g.winner()
        if w is not None:
            print({BLACK: "黑方胜！", WHITE: "白方胜！", 0: "和棋。"}[w])
            return
        if g.turn == human:
            caps = g.captures(human)
            if caps:
                print(f"有吃必吃！可选 {len(g.legal_moves(human))} 条最多吃子路线。")
            try:
                s = input("走法> ").strip()
            except EOFError:
                return
            if s.lower() == "q":
                return
            try:
                path = [parse_coord(t) for t in s.replace("-", " ").split()]
                if len(path) < 2:
                    raise ValueError("至少需要起点和终点")
                g.apply_path(human, path)
            except ValueError as e:
                print("无效：", e)
        else:
            m = ai_move(g, BLACK, rng)
            g.apply_path(BLACK, m)
            print("白方走：", "-".join(f"{'abcde'[c]}{5 - r}" for r, c in m))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Alquerque 阿爾克棋：古老跳吃棋")
    ap.add_argument("--auto", action="store_true", help="AI 对 AI 自动演示")
    ap.add_argument("--games", type=int, default=10, help="自动演示局数")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--verbose", action="store_true", help="打印每局结果")
    args = ap.parse_args(argv)
    if args.auto:
        play_auto(args.games, args.seed, args.verbose)
    else:
        if not sys.stdin.isatty():
            print("交互模式需要终端；无头演示请用 --auto。", file=sys.stderr)
            return 2
        play_interactive(args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
