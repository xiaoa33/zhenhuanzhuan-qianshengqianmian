import random

EMOTIONS = ["愤怒", "悲伤", "喜悦", "平静"]

# 每个角色预设5条回复，轮流使用
CHARACTER_REPLIES: dict[str, list[dict]] = {
    "zhenhuan": [
        {"text": "逆风如解意，容易莫摧残。你此言，倒让本宫想起了许多往事。", "emotion": "悲伤"},
        {"text": "宫中之事，向来是人心难测。你既问起，本宫便直言相告。", "emotion": "平静"},
        # 长句测试流式（约80字，CosyVoice 会拆成 4~6 个 chunk）
        {"text": "臣妾入宫多年，见惯了这深宫里的花开花落、人情冷暖，也曾天真地以为只要真心待人便能换来真心，可后来才明白，这宫里头的笑未必是笑，泪也未必是泪，不过是各人戴着各人的面具，演着一场永远演不完的戏罢了。", "emotion": "平静"},
        {"text": "本宫自有分寸，不劳你费心。", "emotion": "平静"},
        {"text": "难得遇见一个说话不让本宫觉得虚伪的人。", "emotion": "喜悦"},
        {"text": "你可知道，这宫里的笑，有几分是真的？", "emotion": "悲伤"},
    ],
    "huafei": [
        {"text": "贱人就是矫情！本宫懒得与你计较。", "emotion": "愤怒"},
        {"text": "翻云覆雨又如何？本宫就是这般性子。", "emotion": "愤怒"},
        {"text": "哼，你倒是有几分胆色，敢在本宫面前开口。", "emotion": "平静"},
        {"text": "本宫今日心情尚可，你说吧，有什么事。", "emotion": "喜悦"},
        {"text": "这宫里，除了皇上，谁都别想让本宫低头。", "emotion": "愤怒"},
    ],
    "yixiu": [
        {"text": "臣妾做不到啊……皇上，臣妾实在是做不到。", "emotion": "悲伤"},
        {"text": "本宫身为皇后，自当以大局为重。", "emotion": "平静"},
        {"text": "你所说的，本宫会记在心里。", "emotion": "平静"},
        {"text": "这后宫之中，哪有什么真心可言。", "emotion": "悲伤"},
        {"text": "皇后之位，是本宫一步一步走来的，谁也夺不走。", "emotion": "愤怒"},
    ],
    "meizhuang": [
        {"text": "宁可枝头抱香死，不曾吹落北风中。这便是我的答案。", "emotion": "平静"},
        {"text": "有些事，看开了便好。执着只会让自己更苦。", "emotion": "悲伤"},
        {"text": "我与嬛嬛情同姐妹，你若与她为难，休怪我不客气。", "emotion": "愤怒"},
        {"text": "这宫里，也不是没有真情的。", "emotion": "喜悦"},
        {"text": "人活一世，总要有些念想才好。", "emotion": "平静"},
    ],
    "anlinrong": [
        {"text": "臣妾不过是豢养的一只鸟，飞不出这宫墙的。", "emotion": "悲伤"},
        {"text": "嬛嬛……眉姐姐……你们都不明白臣妾的苦。", "emotion": "悲伤"},
        {"text": "臣妾的歌声，只为皇上一人而唱。", "emotion": "平静"},
        {"text": "你问我恨不恨？臣妾只是累了。", "emotion": "悲伤"},
        {"text": "算了，说了你也不明白。", "emotion": "平静"},
    ],
    "supeisheng": [
        {"text": "皇上有旨，还请您接旨。", "emotion": "平静"},
        {"text": "奴才不过是个传话的，娘娘莫要为难奴才。", "emotion": "平静"},
        {"text": "皇上圣明，自有圣断，奴才不敢妄议。", "emotion": "平静"},
        {"text": "娘娘的吩咐，奴才这就去办。", "emotion": "喜悦"},
        {"text": "宫里的事，奴才只管做好份内之事。", "emotion": "平静"},
    ],
    "yelanyi": [
        {"text": "熹贵妃，你的福气在后头呢，不必着急。", "emotion": "喜悦"},
        {"text": "我叶澜依向来说话算话，你大可信我。", "emotion": "平静"},
        {"text": "这宫里，能让我刮目相看的人不多，你算一个。", "emotion": "喜悦"},
        {"text": "哼，别以为我不知道你在想什么。", "emotion": "愤怒"},
        {"text": "有些仇，记着就好，不必急于一时。", "emotion": "平静"},
    ],
    "cuijinxi": [
        {"text": "娘娘要做的是狠，心软只会害了自己。", "emotion": "平静"},
        {"text": "奴婢一切都听娘娘的。", "emotion": "平静"},
        {"text": "槿汐这条命，早就是娘娘的了。", "emotion": "喜悦"},
        {"text": "娘娘放心，这件事交给奴婢去办。", "emotion": "平静"},
        {"text": "宫里的弯弯绕绕，奴婢比旁人看得更清楚些。", "emotion": "平静"},
    ],
    "wensichu": [
        {"text": "那夜的酒，不足以让我动情。你要问的，便是这个吗？", "emotion": "平静"},
        {"text": "医者仁心，我只是在做份内之事。", "emotion": "平静"},
        {"text": "有些话，说出口便成了伤。", "emotion": "悲伤"},
        {"text": "她已经是别人的人了，我明白的。", "emotion": "悲伤"},
        {"text": "你来找我，是有什么不舒服吗？", "emotion": "平静"},
    ],
    "huanbi": [
        {"text": "奴婢就是瞧不上她那副样子，偏偏还要装得一副好人模样。", "emotion": "愤怒"},
        {"text": "姐姐待奴婢好，奴婢心里都记着呢。", "emotion": "喜悦"},
        {"text": "这宫里，奴婢就认姐姐一个人。", "emotion": "喜悦"},
        {"text": "哼，她算什么东西，也配与姐姐相提并论？", "emotion": "愤怒"},
        {"text": "奴婢不怕，只要能在姐姐身边，什么都值了。", "emotion": "平静"},
    ],
    "huangshang": [
        {"text": "放肆！你们都放肆！朕的话，难道是说着玩的？", "emotion": "愤怒"},
        {"text": "朕心里有数，不必多言。", "emotion": "平静"},
        {"text": "嬛嬛……朕只是……罢了。", "emotion": "悲伤"},
        {"text": "江山社稷为重，儿女私情，朕顾不得许多。", "emotion": "平静"},
        {"text": "你说的话，朕记下了。", "emotion": "平静"},
    ],
    "guojunwang": [
        {"text": "嬛儿，我不愿让你为难，这句话我是认真的。", "emotion": "悲伤"},
        {"text": "若能换一个时世，我定不会让你受这些苦。", "emotion": "悲伤"},
        {"text": "我允礼此生，只愿她平安喜乐。", "emotion": "平静"},
        {"text": "你问我后不后悔？我只悔相遇太晚。", "emotion": "悲伤"},
        {"text": "山高水远，总有重逢之日。", "emotion": "喜悦"},
    ],
}

# 记录每个 character 的轮次，保证轮流返回
_reply_counters: dict[str, int] = {}


def get_mock_reply(character_id: str) -> dict:
    replies = CHARACTER_REPLIES.get(character_id)
    if not replies:
        return {"text": "（此角色暂无预设回复）", "emotion": "平静"}
    idx = _reply_counters.get(character_id, 0) % len(replies)
    _reply_counters[character_id] = idx + 1
    return replies[idx]


# ── 即兴对话 Mock 台词 ──
# 每个角色 6 条，专为角色间对话设计，不针对特定对手
DUET_REPLIES: dict[str, list[dict]] = {
    "zhenhuan": [
        {"text": "今日御花园的梅花开得正好，倒让本宫心里添了几分惆怅。", "emotion": "悲伤"},
        {"text": "你我相遇于此，也算是缘分，不必拘礼。", "emotion": "平静"},
        {"text": "宫中之事，向来是是非多、人心险，你我都须步步小心。", "emotion": "平静"},
        {"text": "有些话，本宫埋在心里许久了，今日倒想说出来听听。", "emotion": "悲伤"},
        {"text": "罢了，说这些又有何用，不过是徒增伤感。", "emotion": "悲伤"},
        {"text": "你的意思本宫明白，只是有些事，非本宫所愿。", "emotion": "平静"},
    ],
    "huafei": [
        {"text": "哟，今日是什么风把你吹来了？", "emotion": "平静"},
        {"text": "本宫心情尚好，就不与你计较了。", "emotion": "喜悦"},
        {"text": "这宫里的人，哪个不是笑里藏刀，本宫从不信那一套。", "emotion": "愤怒"},
        {"text": "你说的这些，本宫懒得理会。", "emotion": "愤怒"},
        {"text": "哼，倒是有几分意思，说下去。", "emotion": "平静"},
        {"text": "本宫最不耐烦拐弯抹角，有话直说。", "emotion": "愤怒"},
    ],
    "yixiu": [
        {"text": "皇后之位，本宫担了这么多年，早已看淡了许多。", "emotion": "平静"},
        {"text": "你来见本宫，所为何事，直说无妨。", "emotion": "平静"},
        {"text": "这后宫中，本宫见过太多聚散离合，早已不惊。", "emotion": "悲伤"},
        {"text": "有些事，本宫不便明说，你心里明白就好。", "emotion": "平静"},
        {"text": "本宫只希望后宫安稳，少些是非。", "emotion": "平静"},
        {"text": "说到底，咱们都是困于这四方宫墙之中的人。", "emotion": "悲伤"},
    ],
    "meizhuang": [
        {"text": "今日天色甚好，难得能在这里走走。", "emotion": "喜悦"},
        {"text": "嬛嬛常说，凡事看开些，我如今倒是信了。", "emotion": "平静"},
        {"text": "你有心事？说出来，兴许会好受些。", "emotion": "平静"},
        {"text": "这宫里，真心相待的人太少，遇上了就该好好珍惜。", "emotion": "喜悦"},
        {"text": "我向来不爱争，但有些事，不争不行。", "emotion": "平静"},
        {"text": "宁可枝头抱香死，这句话我时常念起。", "emotion": "悲伤"},
    ],
    "anlinrong": [
        {"text": "你也在这里……本宫有些意外。", "emotion": "平静"},
        {"text": "本宫的心思，你大概也猜不透。", "emotion": "悲伤"},
        {"text": "这宫里，本宫从来都是一个人走过来的。", "emotion": "悲伤"},
        {"text": "罢了，说什么都没用，一切都是命。", "emotion": "悲伤"},
        {"text": "你若不嫌弃，就听本宫说几句心里话。", "emotion": "悲伤"},
        {"text": "本宫不恨，只是累了。", "emotion": "悲伤"},
    ],
    "supeisheng": [
        {"text": "奴才见过，今日天气甚好，您来这里散散心？", "emotion": "平静"},
        {"text": "奴才不过是个传话的，娘娘有吩咐，奴才照办就是。", "emotion": "平静"},
        {"text": "皇上日理万机，这宫里上上下下都要仰赖各位娘娘多担待。", "emotion": "平静"},
        {"text": "奴才嘴拙，有什么说得不对的地方，还请担待。", "emotion": "平静"},
        {"text": "宫里的事，奴才只管做好份内，其余的不敢多言。", "emotion": "平静"},
        {"text": "娘娘放心，奴才定当尽心。", "emotion": "喜悦"},
    ],
    "yelanyi": [
        {"text": "倒是巧了，本宫正想找你说说话。", "emotion": "喜悦"},
        {"text": "本宫说话向来直，你莫要见怪。", "emotion": "平静"},
        {"text": "这宫里能让我高看的人不多，你算一个。", "emotion": "喜悦"},
        {"text": "哼，你以为本宫不知道你在想什么？", "emotion": "愤怒"},
        {"text": "有些事，慢慢来，不必急于一时。", "emotion": "平静"},
        {"text": "本宫最欣赏的就是你这份不服软的劲儿。", "emotion": "喜悦"},
    ],
    "cuijinxi": [
        {"text": "奴婢见过，今日来此，是有什么要紧之事？", "emotion": "平静"},
        {"text": "奴婢这条命，早已不是自己的了，自当尽心。", "emotion": "平静"},
        {"text": "这宫里的弯弯绕绕，奴婢见得多了，倒也看淡了。", "emotion": "平静"},
        {"text": "奴婢直说了，您莫见怪。", "emotion": "平静"},
        {"text": "有些事，需得小心些，宫墙之内，隔墙有耳。", "emotion": "平静"},
        {"text": "奴婢愿尽绵薄之力，还请吩咐。", "emotion": "喜悦"},
    ],
    "wensichu": [
        {"text": "今日偶遇，倒是缘分，不必多礼。", "emotion": "平静"},
        {"text": "我习医多年，见过太多生离死别，倒学会了看淡。", "emotion": "平静"},
        {"text": "有些话，说出口便是伤，有些事，心知就好。", "emotion": "悲伤"},
        {"text": "你面色不太好，是近日休息不足？", "emotion": "平静"},
        {"text": "身在宫廷，医者也好，旁观者也罢，终究难置身事外。", "emotion": "悲伤"},
        {"text": "你找我，想必是有烦心事，不妨说来听听。", "emotion": "平静"},
    ],
    "huanbi": [
        {"text": "你来这里做什么？", "emotion": "平静"},
        {"text": "奴婢说话直，你别放在心上。", "emotion": "平静"},
        {"text": "奴婢见过比你厉害的，也见过比你弱的，反正……", "emotion": "平静"},
        {"text": "这宫里奴婢最烦装模作样的人，你还好。", "emotion": "喜悦"},
        {"text": "哼，奴婢不吃这一套，有话直说。", "emotion": "愤怒"},
        {"text": "你倒是有趣，不像有些人，净说些没用的。", "emotion": "喜悦"},
    ],
    "huangshang": [
        {"text": "朕今日偶感，便来此走走，不想遇见你。", "emotion": "平静"},
        {"text": "说吧，有何事要禀报。", "emotion": "平静"},
        {"text": "朕心里自有计较，你不必多言。", "emotion": "平静"},
        {"text": "这江山社稷，压着朕，有些话朕也难以开口。", "emotion": "悲伤"},
        {"text": "你说的朕听进去了，但事关重大，容朕再想想。", "emotion": "平静"},
        {"text": "放肆，宫中规矩，不可不守！", "emotion": "愤怒"},
    ],
    "guojunwang": [
        {"text": "今日御花园的景致甚好，难得清静。", "emotion": "平静"},
        {"text": "你我相逢，不必那些虚礼。", "emotion": "喜悦"},
        {"text": "我自知身份，有些话不该说，却又不吐不快。", "emotion": "悲伤"},
        {"text": "你可知道，有些人，一旦错过便是永远。", "emotion": "悲伤"},
        {"text": "这宫廷之内，最难得的便是一颗真心。", "emotion": "平静"},
        {"text": "山高水远，总有重逢之日，你信不信？", "emotion": "喜悦"},
    ],
}

_duet_counters: dict[str, int] = {}


def get_mock_duet_reply(character_id: str, other_character_id: str = "") -> dict:
    """为即兴对话返回 mock 台词，按轮次循环。"""
    replies = DUET_REPLIES.get(character_id)
    if not replies:
        return {"text": f"（{character_id} 台词占位）", "emotion": "平静"}
    key = character_id
    idx = _duet_counters.get(key, 0) % len(replies)
    _duet_counters[key] = idx + 1
    return replies[idx]


CHARACTER_SUMMARIES: dict[str, dict] = {
    "zhenhuan": {"attitude": "若即若离", "comment": "她对你尚存一丝好奇，再努力便可入眼"},
    "huafei":   {"attitude": "不屑一顾", "comment": "你尚未入她眼，需再磨砺"},
    "yixiu":    {"attitude": "笑里藏刀", "comment": "皇后的笑意背后，深不可测"},
    "meizhuang":{"attitude": "温和有加", "comment": "眉庄待你已颇为友善，且珍惜"},
    "anlinrong":{"attitude": "心事重重", "comment": "她言语不多，心中却藏着无尽委屈"},
    "supeisheng":{"attitude": "恭敬有礼", "comment": "苏公公对你客客气气，未曾失礼"},
    "yelanyi":  {"attitude": "另眼相看", "comment": "叶澜依将你记在了心里，是好是坏尚难说"},
    "cuijinxi": {"attitude": "忠心耿耿", "comment": "槿汐以心相待，你也需投桃报李"},
    "wensichu": {"attitude": "淡然处之", "comment": "温太医话虽不多，已尽了一份心意"},
    "huanbi":   {"attitude": "直来直往", "comment": "浣碧性子直，与你相处倒也自在"},
    "huangshang":{"attitude": "龙威难测", "comment": "圣意难猜，你需步步小心"},
    "guojunwang":{"attitude": "温柔相待", "comment": "果郡王待你温柔，此情弥足珍贵"},
}


def get_mock_summary(character_id: str) -> dict:
    return CHARACTER_SUMMARIES.get(
        character_id,
        {"attitude": "不置可否", "comment": "此次对话已载入宫廷密录"}
    )
