#!/usr/bin/env python3
"""甄嬛传 14 角色 speaker 注册脚本 — 运行一次即可持久化到 spk2info.pt

用法（在 AutoDL 训练服务器上）:
    cd /root/autodl-tmp
    python register_speakers.py

前置条件:
    1. zero_shot_data/ 已上传到 /root/autodl-tmp/data/zero_shot_data/
    2. CosyVoice 预训练模型在 pretrained_models/Fun-CosyVoice3-0.5B/
"""
import sys
sys.path.append('/root/autodl-tmp/CosyVoice/third_party/Matcha-TTS')
from cosyvoice.cli.cosyvoice import AutoModel

# 预训练模型路径
MODEL_DIR = '/root/autodl-tmp/CosyVoice/pretrained_models/Fun-CosyVoice3-0.5B'
DATA_DIR = '/root/autodl-tmp/data/zero_shot_data'

cosyvoice = AutoModel(model_dir=MODEL_DIR)

speakers = {
    # ===== 1. 甄嬛 =====
    '甄嬛': (
        '不如你回去时把我抄好的经文送去宝华殿捎给那孩子',
        f'{DATA_DIR}/甄嬛/zhenhuan_2069.wav',
    ),
    # ===== 2. 皇上 =====
    '皇上': (
        '这几日朕虽然病着心却惦记着你这里你可有再来等朕吗',
        f'{DATA_DIR}/皇上·爱新觉罗·胤禎/huangshang_0141.wav',
    ),
    # ===== 3. 皇后 =====
    '皇后': (
        '初闻只是感觉清淡闻久了牡丹那种雍容的底蕴才会缓缓渗透出来沁人心脾呀',
        f'{DATA_DIR}/乌拉那拉·宜修(皇后)/huanghou_0366.wav',
    ),
    # ===== 4. 华妃 =====
    '华妃': (
        '哥哥在前朝替皇上效力臣妾在后宫为皇上尽心',
        f'{DATA_DIR}/华妃·年世兰/huafei_0087.wav',
    ),
    # ===== 5. 沈眉庄 =====
    '沈眉庄': (
        '臣妾想与其等公主大了再挪腾地方不如现在就让臣妾搬去碎玉轩居住吧',
        f'{DATA_DIR}/沈眉庄/meizhuang_0389.wav',
    ),
    # ===== 6. 安陵容 =====
    '安陵容': (
        '听闻夏姐姐出身骁勇世家妹妹好生景仰',
        f'{DATA_DIR}/安陵容/anlingrong_0016.wav',
    ),
    # ===== 7. 苏培盛 =====
    '苏培盛': (
        '华妃呃年嫔娘娘来了要求面圣怎么回事啊年嫔娘娘带着江城江慎两位太医来说是一定要见皇上似乎是有急事',
        f'{DATA_DIR}/苏培盛/supeisheng_0121.wav',
    ),
    # ===== 8. 叶澜依 =====
    '叶澜依': (
        '何况这满殿里坐着的人谁知有哪个是口是心非的呢',
        f'{DATA_DIR}/叶澜依/yelanyi_0275.wav',
    ),
    # ===== 9. 崔槿汐 =====
    '崔槿汐': (
        '此番之事奴婢也是有责任的奴婢只是觉得那件衣裳眼熟可怎么也没有想起来那是纯元皇后的旧衣',
        f'{DATA_DIR}/崔槿汐/cuijinxi_0372.wav',
    ),
    # ===== 10. 温实初 =====
    '温实初': (
        '娘娘素来胃寒若在因为饮食不调而伤了脾胃岂不是亏了身子吗',
        f'{DATA_DIR}/温实初/wenshichu_0206.wav',
    ),
    # ===== 11. 浣碧 =====
    '浣碧': (
        '小主昨日受了惊吓午膳吃不下晚膳也没用',
        f'{DATA_DIR}/浣碧/huanbi_0056.wav',
    ),
    # ===== 12. 果郡王 =====
    '果郡王': (
        '可是我看不如用漂色玉纤纤更见玉足的雪白纤细之妙',
        f'{DATA_DIR}/果郡王·允礼/guojunwang_0023.wav',
    ),
    # ===== 13. 太后 =====
    '太后': (
        '身为皇后是要掌管群花而不是一味的修剪终致花叶凋零',
        f'{DATA_DIR}/太后/taihou_0275.wav',
    ),
    # ===== 14. 曹贵人 =====
    '曹贵人': (
        '华妃生怕日后再度失宠其实自从失去丽萍帮助后她便已有心栽培人手',
        f'{DATA_DIR}/曹贵人/caoguiren_0244.wav',
    ),
}

if __name__ == '__main__':
    print(f'模型: {MODEL_DIR}')
    print(f'注册 {len(speakers)} 个角色...\n')

    ok_count = 0
    for spk_id, (prompt_text, wav_path) in speakers.items():
        # CosyVoice3 要求 prompt_text 含 <|endofprompt|>
        # 格式: instruct<|endofprompt|>prompt_text
        ok = cosyvoice.add_zero_shot_spk(
            f'You are a helpful assistant.<|endofprompt|>{prompt_text}',
            wav_path, spk_id)
        status = '✅' if ok else '❌'
        if ok:
            ok_count += 1
        print(f'{status} {spk_id}')

    cosyvoice.save_spkinfo()
    print(f'\n💾 {ok_count}/{len(speakers)} 个角色已保存到 spk2info.pt')
    print(f'📋 可用 speaker 列表: {cosyvoice.list_available_spks()}')
