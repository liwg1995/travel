# _*_ coding:utf-8 _*_
import os
import uuid
from datetime import datetime
from functools import wraps

from flask import render_template, redirect, url_for, flash, session, request, make_response, current_app
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from app import db
from app.admin.forms import LoginForm, PwdForm, AreaForm, ScenicForm, TravelsForm
from app.models import Admin, Adminlog, Oplog, Userlog, Area, User, Suggestion, Scenic, Travels
from . import admin


def admin_login(f):
    """
    登录装饰器
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin" not in session:
            return redirect(url_for("admin.login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


def addOplog(reason):
    oplog = Oplog(
        admin_id=session["admin_id"],
        ip=request.remote_addr,
        reason=reason
    )
    db.session.add(oplog)
    db.session.commit()


def gen_rnd_filename():
    return datetime.now().strftime("%Y%m%d%H%M%S") + str(uuid.uuid4().hex)


def change_filename(filename):
    """
    修改文件名称
    """
    fileinfo = os.path.splitext(filename)
    filename = gen_rnd_filename() + fileinfo[-1]
    return filename


@admin.route("/")
@admin_login
def index():
    return render_template("admin/index.html")


@admin.route("/login/", methods=["GET", "POST"])
def login():
    """
    登录功能
    """
    form = LoginForm()  # 实例化登录表单
    if form.validate_on_submit():  # 验证提交表单
        data = form.data  # 接收数据
        admin = Admin.query.filter_by(name=data["account"]).first()  # 查找Admin表数据
        # 密码错误时，check_pwd返回false,则此时not check_pwd(data["pwd"])为真。
        if not admin.check_pwd(data["pwd"]):
            flash("密码错误!", "err")  # 闪存错误信息
            return redirect(url_for("admin.login"))  # 跳转到后台登录页
        # 如果是正确的，就要定义session的会话进行保存。
        session["admin"] = data["account"]  # 存入session
        session["admin_id"] = admin.id  # 存入session
        # 创建数据
        adminlog = Adminlog(
            admin_id=admin.id,
            ip=request.remote_addr,
        )
        db.session.add(adminlog)  # 添加数据
        db.session.commit()  # 提交数据
        return redirect(url_for("admin.index"))  # 返回后台主页

    return render_template("admin/login.html", form=form)


@admin.route('/logout/')
@admin_login
def logout():
    """
    后台注销登录
    """
    session.pop("admin", None)
    session.pop("admin_id", None)
    return redirect(url_for("admin.login"))


@admin.route('/pwd/', methods=["GET", "POST"])
@admin_login
def pwd():
    """
    后台密码修改
    """
    form = PwdForm()
    if form.validate_on_submit():
        data = form.data
        admin = Admin.query.filter_by(name=session["admin"]).first()
        from werkzeug.security import generate_password_hash
        admin.pwd = generate_password_hash(data["new_pwd"])
        db.session.add(admin)
        db.session.commit()
        flash("修改密码成功，请重新登录！", "ok")
        return redirect(url_for('admin.logout'))
    return render_template("admin/pwd.html", form=form)


@admin.route("/user/list/", methods=["GET"])
@admin_login
def user_list():
    """
    会员列表
    """
    page = request.args.get('page', 1, type=int)  # 获取page参数值
    keyword = request.args.get('keyword', '', type=str)

    if keyword:
        # 根据姓名或者邮箱查询
        filters = or_(User.username == keyword, User.email == keyword)
        page_data = User.query.filter(filters).order_by(
            User.addtime.desc()
        ).paginate(page=page, per_page=5)
    else:
        page_data = User.query.order_by(
            User.addtime.desc()
        ).paginate(page=page, per_page=5)

    return render_template("admin/user_list.html", page_data=page_data)


@admin.route("/user/view/<int:id>/", methods=["GET"])
@admin_login
def user_view(id=None):
    """
    查看会员详情
    """
    from_page = request.args.get('fp')
    if not from_page:
        from_page = 1
    user = User.query.get_or_404(int(id))
    return render_template("admin/user_view.html", user=user, from_page=from_page)


@admin.route("/user/del/<int:id>/", methods=["GET"])
@admin_login
def user_del(id=None):
    """
    删除会员
    """
    page = request.args.get('page', 1, type=int)
    user = User.query.get_or_404(int(id))
    db.session.delete(user)
    db.session.commit()
    addOplog("删除会员" + user.name)  # 添加日志
    flash("删除会员成功！", "ok")
    return redirect(url_for('admin.user_list', page=page))


@admin.route("/suggestion_list/list/", methods=["GET"])
@admin_login
def suggestion_list():
    """
    意见建议列表
    """
    page = request.args.get('page', 1, type=int)  # 获取page参数值
    page_data = Suggestion.query.order_by(
        Suggestion.addtime.desc()
    ).paginate(page=page, per_page=5)
    return render_template("admin/suggestion_list.html", page_data=page_data)


@admin.route("/suggestion/del/<int:id>/", methods=["GET"])
@admin_login
def suggestion_del(id=None):
    """
    删除会员
    """
    page = request.args.get('page', 1, type=int)
    suggestion = Suggestion.query.get_or_404(int(id))
    db.session.delete(suggestion)
    db.session.commit()
    addOplog("删除意见建议")  # 添加日志
    flash("删除成功！", "ok")
    return redirect(url_for('admin.suggestion_list', page=page))


@admin.route('/area/add/', methods=["GET", "POST"])
@admin_login
def area_add():
    """
    添加地区
    """
    form = AreaForm()
    if form.validate_on_submit():
        data = form.data  # 接收数据
        area = Area.query.filter_by(name=data["name"]).count()
        # 说明已经有这个地区了
        if area == 1:
            flash("地区已存在", "err")
            return redirect(url_for("admin.area_add"))
        area = Area(
            name=data["name"],
            is_recommended=data['is_recommended'],
            introduction=data['introduction']
        )
        db.session.add(area)
        db.session.commit()
        addOplog("添加地区" + data["name"])  # 添加日志
        flash("地区添加成功", "ok")
        return redirect(url_for("admin.area_add"))
    return render_template("admin/area_add.html", form=form)


@admin.route("/area/edit/<int:id>", methods=["GET", "POST"])
@admin_login
def area_edit(id=None):
    """
    地区编辑
    """
    form = AreaForm()
    form.submit.label.text = "修改"
    area = Area.query.get_or_404(id)
    if request.method == "GET":
        form.name.data = area.name
        form.is_recommended.data = area.is_recommended
        form.introduction.data = area.introduction
    if form.validate_on_submit():
        data = form.data
        area_count = Area.query.filter_by(name=data["name"]).count()
        if area.name != data["name"] and area_count == 1:
            flash("地区已存在", "err")
            return redirect(url_for("admin.area_edit", id=area.id))
        area.name = data["name"]
        area.is_recommended = int(data["is_recommended"])
        area.introduction = data["introduction"]
        db.session.add(area)
        db.session.commit()
        flash("地区修改成功", "ok")
        return redirect(url_for("admin.area_edit", id=area.id))
    return render_template("admin/area_edit.html", form=form, area=area)


@admin.route("/area/list/", methods=["GET"])
@admin_login
def area_list():
    """
    标签列表
    """
    name = request.args.get('name', type=str)  # 获取name参数值
    page = request.args.get('page', 1, type=int)  # 获取page参数值
    if name:  # 搜索功能
        page_data = Area.query.filter_by(name=name).order_by(
            Area.addtime.desc()
        ).paginate(page=page, per_page=5)
    else:
        # 查找数据
        page_data = Area.query.order_by(
            Area.addtime.desc()
        ).paginate(page=page, per_page=5)
    return render_template("admin/area_list.html", page_data=page_data)  # 渲染模板


@admin.route("/area/del/<int:id>/", methods=["GET"])
@admin_login
def area_del(id=None):
    """
    标签删除
    """
    # filter_by在查不到或多个的时候并不会报错，get会报错。
    area = Area.query.filter_by(id=id).first_or_404()
    db.session.delete(area)
    db.session.commit()
    addOplog("删除地区" + area.name)  # 添加日志
    flash("地区<<{0}>>删除成功".format(area.name), "ok")
    return redirect(url_for("admin.area_list"))


@admin.route("/oplog/list/", methods=["GET"])
@admin_login
def oplog_list():
    """
    操作日志管理
    """
    page = request.args.get('page', 1, type=int)  # 获取page参数值
    page_data = Oplog.query.join(
        Admin
    ).filter(
        Admin.id == Oplog.admin_id,
    ).order_by(
        Oplog.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("admin/oplog_list.html", page_data=page_data)


@admin.route("/adminloginlog/list/", methods=["GET"])
@admin_login
def adminloginlog_list(page=None):
    """
    管理员登录日志
    """
    page = request.args.get('page', 1, type=int)  # 获取page参数值
    page_data = Adminlog.query.join(
        Admin
    ).filter(
        Admin.id == Adminlog.admin_id,
    ).order_by(
        Adminlog.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("admin/adminloginlog_list.html", page_data=page_data)


@admin.route("/userloginlog/list/", methods=["GET"])
@admin_login
def userloginlog_list(page=None):
    """
    会员登录日志列表
    """
    page = request.args.get('page', 1, type=int)  # 获取page参数值
    page_data = Userlog.query.join(
        User
    ).filter(
        User.id == Userlog.user_id,
    ).order_by(
        Userlog.addtime.desc()
    ).paginate(page=page, per_page=5)
    return render_template("admin/userloginlog_list.html", page_data=page_data)


@admin.route("/scenic/add/", methods=["GET", "POST"])
@admin_login
def scenic_add():
    """
    添加景区页面
    """
    form = ScenicForm()  # 实例化form表单
    form.area_id.choices = [(v.id, v.name) for v in Area.query.all()]  # 为area_id添加属性
    if form.validate_on_submit():
        data = form.data
        # 判断景区是否存在    
        scenic_count = Scenic.query.filter_by(title=data["title"]).count()
        # 判断是否有重复数据。
        if scenic_count == 1:
            flash("景点已经存在！", "err")
            return redirect(url_for('admin.scenic_add'))

        file_logo = secure_filename(form.logo.data.filename)  # 确保文件名
        if not os.path.exists(current_app.config["UP_DIR"]):
            # 创建一个多级目录
            os.makedirs(current_app.config["UP_DIR"])  # 创建文件夹
            os.chmod(current_app.config["UP_DIR"], "rw")  # 设置权限
        logo = change_filename(file_logo)  # 更改名称
        form.logo.data.save(current_app.config["UP_DIR"] + logo)  # 保存文件
        # 为Scenic类属性赋值
        scenic = Scenic(
            title=data["title"],
            logo=logo,
            star=int(data["star"]),
            address=data["address"],
            is_hot=int(data["is_hot"]),
            is_recommended=int(data["is_recommended"]),
            area_id=data["area_id"],
            introduction=data["introduction"],
            content=data["content"],
        )
        db.session.add(scenic)  # 添加数据
        db.session.commit()  # 提交数据
        addOplog("添加景区" + data["title"])  # 添加日志
        flash("添加景区成功！", "ok")  # 使用flash保存添加成功信息
        return redirect(url_for('admin.scenic_add'))  # 页面跳转
    return render_template("admin/scenic_add.html", form=form)  # 渲染模板


@admin.route("/scenic/list/", methods=["GET"])
@admin_login
def scenic_list():
    """
    景区列表页面
    """
    title = request.args.get('title', '', type=str)  # 获取查询标题
    page = request.args.get('page', 1, type=int)  # 获取page参数值
    if title:  # 根据标题搜索景区
        page_data = Scenic.query.filter_by(title=title).order_by(
            Scenic.addtime.desc()  # 根据添加时间降序
        ).paginate(page=page, per_page=5)  # 分页
    else:  # 显示全部景区
        page_data = Scenic.query.order_by(
            Scenic.addtime.desc()  # 根据添加时间降序
        ).paginate(page=page, per_page=5)  # 分页
    return render_template("admin/scenic_list.html", page_data=page_data)  # 渲染模板


@admin.route("/scenic/edit/<int:id>/", methods=["GET", "POST"])
@admin_login
def scenic_edit(id=None):
    """
    编辑景区页面
    """
    form = ScenicForm()  # 实例化ScenicForm类
    form.area_id.choices = [(v.id, v.name) for v in Area.query.all()]  # 为area_id添加属性
    form.submit.label.text = "修改"  # 修改提交按钮的文字
    form.logo.validators = []  # 初始化为空
    scenic = Scenic.query.get_or_404(int(id))  # 根据ID查找景区是否存在
    if request.method == "GET":  # 如果以GET方式提交，获取所有景区信息
        form.is_recommended.data = scenic.is_recommended
        form.is_hot.data = scenic.is_hot
        form.area_id.data = scenic.area_id
        form.star.data = scenic.star
        form.content.data = scenic.content
        form.introduction.data = scenic.introduction
    if form.validate_on_submit():  # 如果提交表单
        data = form.data  # 获取表单数据
        scenic_count = Scenic.query.filter_by(title=data["title"]).count()  # 判断标题是否重复
        # 判断是否有重复数据
        if scenic_count == 1 and scenic.title != data["title"]:
            flash("景点已经存在！", "err")
            return redirect(url_for('admin.scenic_edit', id=id))
        if not os.path.exists(current_app.config["UP_DIR"]):  # 判断目录是否存在
            os.makedirs(current_app.config["UP_DIR"])  # 创建目录
            os.chmod(current_app.config["UP_DIR"], "rw")  # 设置读写权限
        # 上传图片
        if form.logo.data != "":
            file_logo = secure_filename(form.logo.data.filename)  # 确保文件名安全
            scenic.logo = change_filename(file_logo)  # 更改文件名
            form.logo.data.save(current_app.config["UP_DIR"] + scenic.logo)  # 保存文件

        # 属性赋值
        scenic.title = data["title"]
        scenic.address = data["address"]
        scenic.area_id = data["area_id"]
        scenic.star = int(data["star"])
        scenic.is_hot = int(data["is_hot"])
        scenic.is_recommended = int(data["is_recommended"])
        scenic.introduction = data["introduction"]
        scenic.content = data["content"]

        db.session.add(scenic)  # 添加数据
        db.session.commit()  # 提交数据
        flash("修改景区成功！", "ok")
        return redirect(url_for('admin.scenic_edit', id=id))  # 跳转到编辑页面
    return render_template("admin/scenic_edit.html", form=form, scenic=scenic)  # 渲染模板，传递变量


@admin.route("/scenic/del/<int:id>/", methods=["GET"])
@admin_login
def scenic_del(id=None):
    """
    景区删除
    """
    scenic = Scenic.query.get_or_404(id)  # 根据景区ID查找数据
    db.session.delete(scenic)  # 删除数据
    db.session.commit()  # 提交数据
    flash("景区删除成功", "ok")  # 使用flash存储成功信息
    addOplog("删除景区" + scenic.title)  # 添加日志
    return redirect(url_for('admin.scenic_list', page=1))  # 渲染模板


@admin.route("/travels/add/", methods=["GET", "POST"])
@admin_login
def travels_add():
    """
    添加游记
    """
    form = TravelsForm()
    form.scenic_id.choices = [(v.id, v.title) for v in Scenic.query.all()]
    if form.validate_on_submit():
        data = form.data
        # 判断游记是否存在    
        travels_count = Travels.query.filter_by(title=data["title"]).count()
        # 判断是否有重复数据。
        if travels_count == 1:
            flash("景点已经存在！", "err")
            return redirect(url_for('admin.travels_add'))
        travels = Travels(
            title=data["title"],
            author=data["author"],
            scenic_id=data["scenic_id"],
            content=data["content"],
        )
        db.session.add(travels)
        db.session.commit()
        addOplog("添加游记" + data["title"])  # 添加日志
        flash("添加游记成功！", "ok")
        return redirect(url_for('admin.travels_add'))
    return render_template("admin/travels_add.html", form=form)


@admin.route("/travels/list/", methods=["GET"])
@admin_login
def travels_list():
    """
    景区列表页面
    """
    keywords = request.args.get('keywords', '', type=str)
    page = request.args.get('page', 1, type=int)  # 获取page参数值
    if keywords:
        # 使用like实现模糊查询
        page_data = Travels.query.filter(Travels.title.like("%" + keywords + "%")).order_by(
            Travels.addtime.desc()
        ).paginate(page=page, per_page=5)
    else:
        page_data = Travels.query.order_by(
            Travels.addtime.desc()
        ).paginate(page=page, per_page=5)
    return render_template("admin/travels_list.html", page_data=page_data)


@admin.route("/travels/edit/<int:id>/", methods=["GET", "POST"])
@admin_login
def travels_edit(id=None):
    """
    编辑游记
    """
    form = TravelsForm()
    form.scenic_id.choices = [(v.id, v.title) for v in Scenic.query.all()]
    form.submit.label.text = "修改"
    travels = Travels.query.get_or_404(int(id))
    if request.method == "GET":
        form.scenic_id.data = travels.scenic_id
        form.content.data = travels.content
    if form.validate_on_submit():
        data = form.data
        travels_count = Travels.query.filter_by(title=data["title"]).count()
        # 判断是否有重复数据
        if travels_count == 1 and travels.title != data["title"]:
            flash("游记已经存在！", "err")
            return redirect(url_for('admin.travels_edit', id=id))

        travels.title = data["title"]
        travels.scenic_id = data["scenic_id"]
        travels.author = data["author"]
        travels.content = data["content"]

        db.session.add(travels)
        db.session.commit()
        flash("修改景区成功！", "ok")
        return redirect(url_for('admin.travels_edit', id=id))
    return render_template("admin/travels_edit.html", form=form, travels=travels)


@admin.route("/travels/del/<int:id>/", methods=["GET"])
@admin_login
def travels_del(id=None):
    """
    景区删除
    """
    travels = Travels.query.get_or_404(id)
    db.session.delete(travels)
    db.session.commit()
    flash("游记删除成功", "ok")
    addOplog("删除游记" + travels.title)  # 添加日志
    return redirect(url_for('admin.travels_list', page=1))


@admin.route('/ckupload/', methods=['POST', 'OPTIONS'])
@admin_login
def ckupload():
    """CKEditor 文件上传"""
    error = ''
    url = ''
    callback = request.args.get("CKEditorFuncNum")

    if request.method == 'POST' and 'upload' in request.files:
        fileobj = request.files['upload']
        fname, fext = os.path.splitext(fileobj.filename)
        rnd_name = '%s%s' % (gen_rnd_filename(), fext)

        filepath = os.path.join(current_app.static_folder, 'uploads/ckeditor', rnd_name)
        print(filepath)
        # 检查路径是否存在，不存在则创建
        dirname = os.path.dirname(filepath)
        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except:
                error = 'ERROR_CREATE_DIR'
        elif not os.access(dirname, os.W_OK):
            error = 'ERROR_DIR_NOT_WRITEABLE'

        if not error:
            fileobj.save(filepath)
            url = url_for('static', filename='%s/%s' % ('uploads/ckeditor', rnd_name))
    else:
        error = 'post error'

    res = """<script type="text/javascript">
  window.parent.CKEDITOR.tools.callFunction(%s, '%s', '%s');
</script>""" % (callback, url, error)

    response = make_response(res)
    response.headers["Content-Type"] = "text/html"
    return response
