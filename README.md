## 注意
- 高版本的python（`3.9`及其以上好像是）可能会出现库的报错，是`flask_wtf`库中的`file.py`文件
> 需要进行如下调整：由这个
```python
from collections import Iterable
```
改为：
```python
from collections.abc import Iterable
```