import importlib
import os
import re
from collections import defaultdict

__current_dir = os.listdir(os.path.dirname(__file__))
AVAILABLE_TEMPLATES = list(
    map(
        lambda x: x.split(".")[0],
        filter(lambda x: x.endswith(".py") and x != "__init__.py", __current_dir),
    )
)


def get_event_template(template_name):
    assert template_name in AVAILABLE_TEMPLATES
    template = importlib.import_module(f".{template_name}", "dee.event_types")
    return template


def get_doc_type(recguid_eventname_eventdict_list):
    doc_type = "unk"
    num_ins = len(recguid_eventname_eventdict_list)
    if num_ins == 0:
        doc_type = "unk"
    elif num_ins == 1:
        doc_type = "o2o"
    else:
        event_types = {x[1] for x in recguid_eventname_eventdict_list}
        if len(event_types) == 1:
            doc_type = "o2m"
        else:
            doc_type = "m2m"
    return doc_type


def get_schema_from_chfinann(data):
    event_type_to_roles = defaultdict(set)
    for _, content in data:
        for _, etype, role_arg_pairs in content["recguid_eventname_eventdict_list"]:
            event_type_to_roles[etype].update(role_arg_pairs.keys())
    return dict(event_type_to_roles)


def generate_event_template_from_trigger_string(
    trigger_string: str, event_type_to_class_name: dict
):
    """
    Args:
        trigger_string: string generated by Data/trigger.py
            破产清算 = {
                    1: ['公司名称'],  # importance: 0.9950641658440277
                    2: ['公司名称', '公告时间'],  # importance: 0.9990128331688055
                    3: ['公司名称', '公告时间', '受理法院'],  # importance: 1.0
                    4: ['公司名称', '公司行业', '公告时间', '受理法院'],  # importance: 1.0
                    5: ['公司名称', '公司行业', '公告时间', '受理法院', '裁定时间'],  # importance: 1.0
            }
            TRIGGERS['all'] = ['公司名称', '公告时间', '受理法院', '裁定时间', '公司行业']
        event_type_to_class_name: {"破产清算": "Liquidation"}
    """
    string_template = """class {class_name}Event(BaseEvent):\n    NAME = "{event_type}"\n    FIELDS = {fields}\n    TRIGGERS = {triggers}\n    TRIGGERS["all"] = {triggers_all}\n    def __init__(self, recguid=None):\n        super().__init__(self.FIELDS, event_name=self.NAME, recguid=recguid)\n        self.set_key_fields(self.TRIGGERS)\n\n"""
    final_string = r"""class BaseEvent(object):
    def __init__(self, fields, event_name="Event", key_fields=(), recguid=None):
        self.recguid = recguid
        self.name = event_name
        self.fields = list(fields)
        self.field2content = {f: None for f in fields}
        self.nonempty_count = 0
        self.nonempty_ratio = self.nonempty_count / len(self.fields)

        self.key_fields = set(key_fields)
        for key_field in self.key_fields:
            assert key_field in self.field2content

    def __repr__(self):
        event_str = "\n{}[\n".format(self.name)
        event_str += "  {}={}\n".format("recguid", self.recguid)
        event_str += "  {}={}\n".format("nonempty_count", self.nonempty_count)
        event_str += "  {}={:.3f}\n".format("nonempty_ratio", self.nonempty_ratio)
        event_str += "] (\n"
        for field in self.fields:
            if field in self.key_fields:
                key_str = " (key)"
            else:
                key_str = ""
            event_str += (
                "  "
                + field
                + "="
                + str(self.field2content[field])
                + ", {}\n".format(key_str)
            )
        event_str += ")\n"
        return event_str

    def update_by_dict(self, field2text, recguid=None):
        self.nonempty_count = 0
        self.recguid = recguid

        for field in self.fields:
            if field in field2text and field2text[field] is not None:
                self.nonempty_count += 1
                self.field2content[field] = field2text[field]
            else:
                self.field2content[field] = None

        self.nonempty_ratio = self.nonempty_count / len(self.fields)

    def field_to_dict(self):
        return dict(self.field2content)

    def set_key_fields(self, key_fields):
        self.key_fields = set(key_fields)

    def is_key_complete(self):
        for key_field in self.key_fields:
            if self.field2content[key_field] is None:
                return False

        return True

    def get_argument_tuple(self):
        args_tuple = tuple(self.field2content[field] for field in self.fields)
        return args_tuple

    def is_good_candidate(self, min_match_count=2):
        key_flag = self.is_key_complete()
        if key_flag:
            if self.nonempty_count >= min_match_count:
                return True
        return False

"""
    groups = re.findall(
        r"\s*(.*?) = ({.*?})\s*TRIGGERS\['all'\] = (\[.*?\])", trigger_string, re.DOTALL
    )
    for event_type, triggers, trigger_all in groups:
        final_string += string_template.format(
            class_name=event_type_to_class_name[event_type],
            event_type=event_type,
            fields=str(trigger_all),
            triggers=str(triggers),
            triggers_all=str(trigger_all),
        )
    event_type2event_class = (
        "{"
        + " ".join(
            [
                f"{event_class_name}Event.NAME: {event_class_name}Event,"
                for event_class_name in event_type_to_class_name.values()
            ]
        )
        + "}"
    )
    event_type_fields_list = (
        "["
        + " ".join(
            [
                f"({event_class_name}Event.NAME, {event_class_name}Event.FIELDS, {event_class_name}Event.TRIGGERS, 2),"
                for event_class_name in event_type_to_class_name.values()
            ]
        )
        + "]"
    )
    final_string += f"\ncommon_fields = []\nevent_type2event_class={event_type2event_class}\n\nevent_type_fields_list={event_type_fields_list}"

    return final_string


if __name__ == "__main__":
    # template = get_event_template("zheng2019")
    # print(template)
    final_string = generate_event_template_from_trigger_string(
        """破产清算 = {
        1: ['公司名称'],  # importance: 0.9950641658440277
        2: ['公司名称', '公告时间'],  # importance: 0.9990128331688055
        3: ['公司名称', '公告时间', '受理法院'],  # importance: 1.0
        4: ['公司名称', '公司行业', '公告时间', '受理法院'],  # importance: 1.0
        5: ['公司名称', '公司行业', '公告时间', '受理法院', '裁定时间'],  # importance: 1.0
}
TRIGGERS['all'] = ['公司名称', '公告时间', '受理法院', '裁定时间', '公司行业']

重大安全事故 = {
        1: ['公司名称'],  # importance: 0.9974424552429667
        2: ['公司名称', '公告时间'],  # importance: 1.0
        3: ['伤亡人数', '公司名称', '公告时间'],  # importance: 1.0
        4: ['伤亡人数', '公司名称', '公告时间', '损失金额'],  # importance: 1.0
        5: ['伤亡人数', '公司名称', '公告时间', '其他影响', '损失金额'],  # importance: 1.0
}
TRIGGERS['all'] = ['公司名称', '公告时间', '伤亡人数', '损失金额', '其他影响']

股东减持 = {
        1: ['减持金额'],  # importance: 0.9486062717770035
        2: ['减持开始日期', '减持金额'],  # importance: 0.9817073170731707
        3: ['减持开始日期', '减持的股东', '减持金额'],  # importance: 0.990418118466899
}
TRIGGERS['all'] = ['减持金额', '减持开始日期', '减持的股东']

股权质押 = {
        1: ['质押金额'],  # importance: 0.9625668449197861
        2: ['质押开始日期', '质押金额'],  # importance: 0.9910873440285205
        3: ['接收方', '质押开始日期', '质押金额'],  # importance: 0.9964349376114082
        4: ['接收方', '质押开始日期', '质押结束日期', '质押金额'],  # importance: 1.0
        5: ['接收方', '质押开始日期', '质押方', '质押结束日期', '质押金额'],  # importance: 1.0
}
TRIGGERS['all'] = ['质押金额', '质押开始日期', '接收方', '质押方', '质押结束日期']

股东增持 = {
        1: ['增持金额'],  # importance: 0.9607609988109393
        2: ['增持的股东', '增持金额'],  # importance: 0.9892984542211652
        3: ['增持开始日期', '增持的股东', '增持金额'],  # importance: 1.0
}
TRIGGERS['all'] = ['增持金额', '增持开始日期', '增持的股东']

股权冻结 = {
        1: ['冻结金额'],  # importance: 0.8524822695035461
        2: ['冻结开始日期', '冻结金额'],  # importance: 0.9687943262411347
        3: ['冻结开始日期', '冻结金额', '被冻结股东'],  # importance: 0.9716312056737588
        4: ['冻结开始日期', '冻结结束日期', '冻结金额', '被冻结股东'],  # importance: 0.9730496453900709
}
TRIGGERS['all'] = ['冻结金额', '冻结开始日期', '被冻结股东', '冻结结束日期']

高层死亡 = {
        1: ['公司名称'],  # importance: 1.0
        2: ['公司名称', '高层人员'],  # importance: 1.0
        3: ['公司名称', '高层人员', '高层职务'],  # importance: 1.0
        4: ['公司名称', '死亡/失联时间', '高层人员', '高层职务'],  # importance: 1.0
        5: ['公司名称', '死亡/失联时间', '死亡年龄', '高层人员', '高层职务'],  # importance: 1.0
}
TRIGGERS['all'] = ['公司名称', '高层人员', '高层职务', '死亡/失联时间', '死亡年龄']

重大资产损失 = {
        1: ['公司名称'],  # importance: 0.9949494949494949
        2: ['公司名称', '公告时间'],  # importance: 1.0
        3: ['公司名称', '公告时间', '损失金额'],  # importance: 1.0
        4: ['公司名称', '公告时间', '其他损失', '损失金额'],  # importance: 1.0
}
TRIGGERS['all'] = ['公司名称', '公告时间', '损失金额', '其他损失']

重大对外赔付 = {
        1: ['公告时间'],  # importance: 0.984251968503937
        2: ['公司名称', '公告时间'],  # importance: 1.0
        3: ['公司名称', '公告时间', '赔付对象'],  # importance: 1.0
        4: ['公司名称', '公告时间', '赔付对象', '赔付金额'],  # importance: 1.0
}
TRIGGERS['all'] = ['公告时间', '公司名称', '赔付对象', '赔付金额']""",
        {
            "破产清算": "Bankruptcy",
            "重大安全事故": "Accident",
            "股东减持": "EquityUnderweight",
            "股权质押": "EquityPledge",
            "股东增持": "EquityOverweight",
            "股权冻结": "EquityFreeze",
            "高层死亡": "LeaderDeath",
            "重大资产损失": "AssetLoss",
            "重大对外赔付": "ExternalIndemnity",
        },
    )
    print(final_string)
