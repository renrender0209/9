from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app import db
from models import User, Notification
import re
from email_validator import validate_email, EmailNotValidError

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('auth/register.html')
    
    try:
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        
        # バリデーション
        errors = []
        
        if not username or len(username) < 3:
            errors.append('ユーザー名は3文字以上で入力してください。')
        if len(username) > 64:
            errors.append('ユーザー名は64文字以内で入力してください。')
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            errors.append('ユーザー名は英数字とアンダースコアのみ使用できます。')
        
        try:
            validate_email(email)
        except EmailNotValidError:
            errors.append('有効なメールアドレスを入力してください。')
        
        if len(password) < 8:
            errors.append('パスワードは8文字以上で入力してください。')
        if password != confirm_password:
            errors.append('パスワードが一致しません。')
        
        # 重複チェック
        if User.query.filter_by(username=username).first():
            errors.append('このユーザー名は既に使用されています。')
        if User.query.filter_by(email=email).first():
            errors.append('このメールアドレスは既に登録されています。')
        
        if errors:
            if request.is_json:
                return jsonify({'success': False, 'errors': errors}), 400
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/register.html')
        
        # ユーザー作成
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # ウェルカム通知
        welcome_notification = Notification(
            user_id=user.id,
            title='ようこそ！',
            message=f'{username}さん、アカウント作成が完了しました。',
            type='success'
        )
        db.session.add(welcome_notification)
        db.session.commit()
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'アカウントが作成されました。'})
        
        flash('アカウントが作成されました。ログインしてください。', 'success')
        return redirect(url_for('auth.login'))
        
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        flash('アカウント作成中にエラーが発生しました。', 'danger')
        return render_template('auth/register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('auth/login.html')
    
    try:
        data = request.get_json() if request.is_json else request.form
        username_or_email = data.get('username_or_email', '').strip()
        password = data.get('password', '')
        remember_me = data.get('remember_me', False)
        
        if not username_or_email or not password:
            error = 'ユーザー名またはメールアドレスとパスワードを入力してください。'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 400
            flash(error, 'danger')
            return render_template('auth/login.html')
        
        # ユーザー検索（ユーザー名またはメールアドレス）
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember_me)
            
            # ログイン通知
            login_notification = Notification(
                user_id=user.id,
                title='ログインしました',
                message='アカウントにログインしました。',
                type='info'
            )
            db.session.add(login_notification)
            db.session.commit()
            
            if request.is_json:
                return jsonify({
                    'success': True, 
                    'message': 'ログインしました。',
                    'user': user.to_dict()
                })
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            error = 'ユーザー名またはパスワードが正しくありません。'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 401
            flash(error, 'danger')
            return render_template('auth/login.html')
            
    except Exception as e:
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        flash('ログイン中にエラーが発生しました。', 'danger')
        return render_template('auth/login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    if request.is_json:
        return jsonify({'success': True, 'message': 'ログアウトしました。'})
    flash('ログアウトしました。', 'info')
    return redirect(url_for('index'))

@auth.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)

@auth.route('/api/user')
@login_required
def api_user():
    """現在のユーザー情報を取得"""
    return jsonify({
        'success': True,
        'user': current_user.to_dict()
    })

@auth.route('/api/user/update', methods=['POST'])
@login_required
def api_update_user():
    """ユーザー情報の更新"""
    try:
        data = request.get_json()
        
        if 'username' in data:
            new_username = data['username'].strip()
            if len(new_username) < 3:
                return jsonify({'success': False, 'error': 'ユーザー名は3文字以上で入力してください。'}), 400
            if not re.match(r'^[a-zA-Z0-9_]+$', new_username):
                return jsonify({'success': False, 'error': 'ユーザー名は英数字とアンダースコアのみ使用できます。'}), 400
            
            existing_user = User.query.filter_by(username=new_username).first()
            if existing_user and existing_user.id != current_user.id:
                return jsonify({'success': False, 'error': 'このユーザー名は既に使用されています。'}), 400
            
            current_user.username = new_username
        
        if 'email' in data:
            new_email = data['email'].strip()
            try:
                validate_email(new_email)
            except EmailNotValidError:
                return jsonify({'success': False, 'error': '有効なメールアドレスを入力してください。'}), 400
            
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user and existing_user.id != current_user.id:
                return jsonify({'success': False, 'error': 'このメールアドレスは既に登録されています。'}), 400
            
            current_user.email = new_email
        
        if 'avatar_url' in data:
            current_user.avatar_url = data['avatar_url']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'プロフィールが更新されました。',
            'user': current_user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@auth.route('/api/user/change-password', methods=['POST'])
@login_required
def api_change_password():
    """パスワード変更"""
    try:
        data = request.get_json()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')
        
        if not current_user.check_password(current_password):
            return jsonify({'success': False, 'error': '現在のパスワードが正しくありません。'}), 400
        
        if len(new_password) < 8:
            return jsonify({'success': False, 'error': '新しいパスワードは8文字以上で入力してください。'}), 400
        
        if new_password != confirm_password:
            return jsonify({'success': False, 'error': 'パスワードが一致しません。'}), 400
        
        current_user.set_password(new_password)
        db.session.commit()
        
        # パスワード変更通知
        notification = Notification(
            user_id=current_user.id,
            title='パスワードが変更されました',
            message='アカウントのパスワードが変更されました。',
            type='warning'
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'パスワードが変更されました。'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500