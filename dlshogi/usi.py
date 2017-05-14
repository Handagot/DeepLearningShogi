import shogi
from dlshogi.policy_network import *
from chainer import serializers

MOVE_FROM_DIRECTION = [
    # (dx, dy, promote)
    (0, 1, False), # UP
    (1, 1, False), # UP_LEFT
    (-1, 1, False), # UP_RIGHT
    (1, 0, False), # LEFT
    (-1, 0, False), # RIGHT
    (0, -1, False), # DOWN
    (1, -1, False), # DOWN_LEFT
    (-1, -1, False), # DOWN_RIGHT
    (0, 1, True), # UP_PROMOTE
    (1, 1, True), # UP_LEFT_PROMOTE
    (-1, 1, True), # UP_RIGHT_PROMOTE
    (1, 0, True), # LEFT_PROMOTE
    (-1, 0, True), # RIGHT_PROMOTE
    (0, -1, True), # DOWN_PROMOTE
    (1, -1, True), # DOWN_LEFT_PROMOTE
    (-1, -1, True), # DOWN_RIGHT_PROMOTE
]

def main():
    while True:
        cmd = input().split(' ', 1)
        print('info string', cmd)

        if cmd[0] == 'usi':
            print('id name dlshogi')
            print('id author Tadao Yamaoka')
            print('usiok')
        elif cmd[0] == 'isready':
            board = shogi.Board()
            model = PolicyNetwork()
            model.to_gpu()
            serializers.load_npz(r'H:\src\DeepLearningShogi\dlshogi\model_epoch11', model)
            print('readyok')
        elif cmd[0] == 'usinewgame':
            continue
        elif cmd[0] == 'position':
            moves = cmd[1].split(' ')
            if moves[0] == 'startpos':
                board.reset()
                for move in moves[2:]:
                    board.push_usi(move)
            print('info string', board.sfen())
        elif cmd[0] == 'go':
            if board.turn == shogi.BLACK:
                piece_bb = board.piece_bb
                occupied = (board.occupied[shogi.BLACK], board.occupied[shogi.WHITE])
                pieces_in_hand = (board.pieces_in_hand[shogi.BLACK], board.pieces_in_hand[shogi.WHITE])
            else:
                piece_bb = [bb_rotate_180(bb) for bb in board.piece_bb]
                occupied = (bb_rotate_180(board.occupied[shogi.WHITE]), bb_rotate_180(board.occupied[shogi.BLACK]))
                pieces_in_hand = (board.pieces_in_hand[shogi.WHITE], board.pieces_in_hand[shogi.BLACK])

            features1, features2, move = make_features((piece_bb, occupied, pieces_in_hand, board.is_check(), None))
            x1 = Variable(cuda.to_gpu(np.array([features1], dtype=np.float32)))
            x2 = Variable(cuda.to_gpu(np.array([features2], dtype=np.float32)))

            y = model(x1, x2, test=True)

            y_data = cuda.to_cpu(y.data)[0]
            
            move_from = None
            move_from_hand = False
            for move_idx, label in enumerate(np.argsort(y_data)[::-1]):
                move_direction_label, move_to = divmod(label, 81)

                for i in range(1, len(PIECE_MOVE_DIRECTION_LABEL) - 1):
                    if move_direction_label < PIECE_MOVE_DIRECTION_LABEL[i + 1]:
                        piece_type = i
                        move_direction_index = move_direction_label - PIECE_MOVE_DIRECTION_LABEL[i]
                        break

                move_direction = PIECE_MOVE_DIRECTION[piece_type][move_direction_index]

                print('info string', 'move_idx', move_idx)
                print('info string', 'piece_type', shogi.PIECE_SYMBOLS[piece_type])
                print('info string', 'move_to', shogi.SQUARE_NAMES[move_to])
                print('info string', 'move_direction', move_direction)
                print('info string', 'y', y_data[label])

                # move from hand
                if move_direction == HAND:
                    if piece_type in pieces_in_hand[0]:
                        move_from_hand = True
                        break
                    continue

                # move from
                (dx, dy, promote) = MOVE_FROM_DIRECTION[move_direction]
                if piece_type == shogi.PAWN:
                    pos = move_to + 9
                    if pos < 81 and occupied[0] & piece_bb[piece_type] & shogi.BB_SQUARES[pos] > 0:
                        move_from = pos
                        break
                elif piece_type == shogi.KNIGHT:
                    move_to_y, move_to_x = divmod(move_to, 9)
                    x = move_to_x + dx
                    y = move_to_y + 2
                    pos = x + y * 9
                    if x in range(0, 9) and y < 9 and occupied[0] & piece_bb[piece_type] & shogi.BB_SQUARES[pos] > 0:
                        move_from = pos
                        break
                elif piece_type in [shogi.SILVER, shogi.GOLD, shogi.KING, shogi.PROM_PAWN, shogi.PROM_LANCE, shogi.PROM_KNIGHT, shogi.PROM_SILVER]:
                    move_to_y, move_to_x = divmod(move_to, 9)
                    x = move_to_x + dx
                    y = move_to_y + dy
                    pos = x + y * 9
                    if x in range(0, 9) and y in range(0, 9) and occupied[0] & piece_bb[piece_type] & shogi.BB_SQUARES[pos] > 0:
                        move_from = pos
                        break
                elif piece_type in [shogi.LANCE, shogi.BISHOP, shogi.ROOK, shogi.PROM_BISHOP, shogi.PROM_ROOK]:
                    move_to_y, move_to_x = divmod(move_to, 9)
                    x = move_to_x
                    y = move_to_y
                    while True:
                        x += dx
                        y += dy
                        if not x in range(0, 9) or not y in range(0, 9):
                            break

                        pos = x + y * 9
                        if occupied[1] & shogi.BB_SQUARES[pos] > 0:
                            break
                        if occupied[0] & shogi.BB_SQUARES[pos] > 0:
                            if piece_bb[piece_type] & shogi.BB_SQUARES[pos] > 0:
                                move_from = pos
                            break

                if move_from:
                    break

            if board.turn == shogi.WHITE:
                move_to = SQUARES_R180[move_to]

            if move_from_hand:
                print('bestmove', shogi.Move(None, move_to, drop_piece_type=piece_type).usi())
            elif move_from:
                if board.turn == shogi.WHITE:
                    move_from = SQUARES_R180[move_from]
                print('bestmove', shogi.Move(move_from, move_to, promote).usi())
            else:
                print('bestmove resign')
        elif cmd[0] == 'quit':
            break

if __name__ == '__main__':
    main()