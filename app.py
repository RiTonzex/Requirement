import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
# pyrefly: ignore [missing-import]
from sqlalchemy import func, UniqueConstraint, event
from sqlalchemy.engine import Engine
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'local-worker-directory-secret-key-12345'

# Database configuration
# If running on Vercel serverless, use the writable /tmp folder for SQLite (100% Free & No Setup)
if os.environ.get('VERCEL'):
    db_path = '/tmp/database.db'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
else:
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Adjust postgres protocol for SQLAlchemy compatibility
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        db_path = os.path.join(app.instance_path, 'database.db')
        os.makedirs(app.instance_path, exist_ok=True)
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Enable Foreign Key support in SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# ==========================================
# DATABASE MODELS
# ==========================================

# Junction Table for Many-to-Many: Worker <-> Skill
worker_skills = db.Table('worker_skills',
    db.Column('worker_id', db.Integer, db.ForeignKey('worker.id', ondelete='CASCADE'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skill.id', ondelete='CASCADE'), primary_key=True)
)

# Junction Table for Many-to-Many: Worker <-> Province (Service Areas)
worker_service_areas = db.Table('worker_service_areas',
    db.Column('worker_id', db.Integer, db.ForeignKey('worker.id', ondelete='CASCADE'), primary_key=True),
    db.Column('province_id', db.Integer, db.ForeignKey('province.id', ondelete='CASCADE'), primary_key=True)
)

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user', 'worker', 'admin'
    fullname = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    
    # 1:1 relationship with Worker (only populated if role == 'worker')
    worker = db.relationship('Worker', backref='user', uselist=False, cascade="all, delete-orphan")
    # 1:Many relationship with Review (reviews written by this user)
    reviews = db.relationship('Review', backref='user', cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Worker(db.Model):
    __tablename__ = 'worker'
    id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True)
    experience = db.Column(db.Integer, default=0)       # experience in years
    starting_price = db.Column(db.Float, default=0.0)    # minimum service fee
    is_available = db.Column(db.Boolean, default=True)   # service availability status
    bio = db.Column(db.Text, nullable=True)              # worker biography / introduction
    
    # Many-to-Many Relationship with Skill
    skills = db.relationship('Skill', secondary=worker_skills, backref=db.backref('workers', lazy='dynamic'))
    # Many-to-Many Relationship with Province (service areas)
    service_areas = db.relationship('Province', secondary=worker_service_areas, backref=db.backref('workers', lazy='dynamic'))
    # 1:Many Relationship with Review (reviews received by this worker)
    reviews_received = db.relationship('Review', backref='worker', cascade="all, delete-orphan")

class SkillCategory(db.Model):
    __tablename__ = 'skill_category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    
    # 1:Many relationship with Skill
    skills = db.relationship('Skill', backref='category', cascade="all, delete-orphan")

class Skill(db.Model):
    __tablename__ = 'skill'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('skill_category.id', ondelete='CASCADE'), nullable=False)

class Province(db.Model):
    __tablename__ = 'province'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    region = db.Column(db.String(50), nullable=True)  # 'ภาคกลาง', 'ภาคเหนือ', 'ภาคใต้', 'ภาคตะวันออก', 'ภาคตะวันตก', etc.

class Review(db.Model):
    __tablename__ = 'review'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker.id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)       # rating score (1-5)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent same user from reviewing same worker multiple times
    __table_args__ = (
        UniqueConstraint('user_id', 'worker_id', name='uq_user_worker_review'),
    )

# ==========================================
# CONTEXT PROCESSORS (For templates)
# ==========================================
@app.context_processor
def inject_global_data():
    try:
        provinces = Province.query.order_by(Province.region, Province.name).all()
        provinces_by_region = {}
        for p in provinces:
            r_name = p.region or 'ภาคอื่นๆ'
            if r_name not in provinces_by_region:
                provinces_by_region[r_name] = []
            provinces_by_region[r_name].append(p)
    except Exception:
        provinces_by_region = {}
    return {
        'now': datetime.utcnow(),
        'provinces_by_region': provinces_by_region
    }

# ==========================================
# ROUTE LOGIC
# ==========================================

# 1. Home / Index Page (Search Form)
@app.route('/')
def index():
    categories = SkillCategory.query.order_by(SkillCategory.name).all()
    provinces = Province.query.order_by(Province.name).all()
    
    # Get featured/top available workers (max 6)
    # Group by Worker.id, calculating avg rating & count
    featured_query = db.session.query(
        Worker,
        func.coalesce(func.avg(Review.rating), 0).label('avg_rating'),
        func.count(Review.id).label('review_count')
    ).outerjoin(Review, Review.worker_id == Worker.id)\
     .join(User, User.id == Worker.id)\
     .filter(Worker.is_available == True)\
     .group_by(Worker.id)\
     .order_by(db.desc('avg_rating'), db.desc('review_count'))\
     .limit(6)
     
    featured_workers = featured_query.all()
    return render_template('index.html', categories=categories, provinces=provinces, featured_workers=featured_workers)

# 2. Authentication: Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        fullname = request.form.get('fullname', '').strip()
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role', 'user')
        
        # Validation
        if not username or not password or not confirm_password or not fullname:
            flash('กรุณากรอกข้อมูลในช่องที่มีเครื่องหมาย * ให้ครบถ้วน', 'danger')
            return render_template('register.html')
            
        if password != confirm_password:
            flash('รหัสผ่านและรหัสผ่านยืนยันไม่ตรงกัน กรุณากรอกใหม่อีกครั้ง', 'danger')
            return render_template('register.html')
            
        if role not in ['user', 'worker']:
            role = 'user'
            
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('ชื่อผู้ใช้นี้ถูกใช้งานแล้ว กรุณาเลือกชื่อผู้ใช้อื่น', 'danger')
            return render_template('register.html')
            
        # Create user
        new_user = User(
            username=username,
            role=role,
            fullname=fullname,
            phone=phone
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit() # commit to get new_user.id
        
        # If worker, create corresponding Worker record
        if role == 'worker':
            new_worker = Worker(
                id=new_user.id,
                experience=0,
                starting_price=0.0,
                is_available=True,
                bio=''
            )
            db.session.add(new_worker)
            db.session.commit()
            
        flash('สมัครสมาชิกสำเร็จแล้ว! กรุณาเข้าสู่ระบบ', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

# 3. Authentication: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['fullname'] = user.fullname
            
            flash(f'ยินดีต้อนรับคุณ {user.fullname} เข้าสู่ระบบ!', 'success')
            if user.role == 'worker':
                return redirect(url_for('profile_edit'))
            return redirect(url_for('index'))
        else:
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'danger')
            
    return render_template('login.html')

# 4. Authentication: Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('ออกจากระบบสำเร็จแล้ว', 'info')
    return redirect(url_for('index'))

# 5. Worker Dashboard: Edit Profile
@app.route('/worker/profile-edit', methods=['GET', 'POST'])
def profile_edit():
    if 'user_id' not in session or session.get('role') != 'worker':
        flash('หน้านี้สำหรับผู้ใช้ที่เป็นช่างเท่านั้น', 'warning')
        return redirect(url_for('login'))
        
    worker = Worker.query.get_or_404(session['user_id'])
    
    if request.method == 'POST':
        fullname = request.form.get('fullname', '').strip()
        phone = request.form.get('phone', '').strip()
        experience = int(request.form.get('experience', 0))
        starting_price = float(request.form.get('starting_price', 0.0))
        bio = request.form.get('bio', '').strip()
        is_available = 'is_available' in request.form
        
        skill_ids = request.form.getlist('skills')
        province_ids = request.form.getlist('provinces')
        
        if not fullname:
            flash('กรุณากรอกชื่อ-นามสกุล', 'danger')
            return redirect(url_for('profile_edit'))
            
        # Update User fields
        worker.user.fullname = fullname
        worker.user.phone = phone
        
        # Update Worker fields
        worker.experience = experience
        worker.starting_price = starting_price
        worker.bio = bio
        worker.is_available = is_available
        
        # Update Many-to-Many Skills
        selected_skills = Skill.query.filter(Skill.id.in_(skill_ids)).all()
        worker.skills = selected_skills
        
        # Update Many-to-Many Service Areas (Provinces)
        selected_provinces = Province.query.filter(Province.id.in_(province_ids)).all()
        worker.service_areas = selected_provinces
        
        db.session.commit()
        session['fullname'] = fullname # Update active session name
        
        flash('บันทึกข้อมูลโปรไฟล์ช่างสำเร็จแล้ว!', 'success')
        return redirect(url_for('profile_edit'))
        
    # GET: Load categories (for nested skills checklist) and provinces
    categories = SkillCategory.query.order_by(SkillCategory.name).all()
    provinces = Province.query.order_by(Province.name).all()
    
    # Pre-select IDs for checkbox active checking
    worker_skill_ids = [s.id for s in worker.skills]
    worker_province_ids = [p.id for p in worker.service_areas]
    
    return render_template(
        'profile_edit.html',
        worker=worker,
        categories=categories,
        provinces=provinces,
        worker_skill_ids=worker_skill_ids,
        worker_province_ids=worker_province_ids
    )

# 6. Search Results & Filters
@app.route('/search_results')
def search_results():
    skill_id = request.args.get('skill_id', type=int)
    province_id = request.args.get('province_id', type=int)
    sort_by = request.args.get('sort_by', 'rating_desc')
    
    # 1. Base Query Joining Worker, User and aggregating Reviews
    query = db.session.query(
        Worker,
        func.coalesce(func.avg(Review.rating), 0).label('avg_rating'),
        func.count(Review.id).label('review_count')
    ).outerjoin(Review, Review.worker_id == Worker.id)\
     .join(User, User.id == Worker.id)\
     .filter(Worker.is_available == True)
     
    # 2. Apply Filters
    if skill_id:
        query = query.filter(Worker.skills.any(Skill.id == skill_id))
    if province_id:
        query = query.filter(Worker.service_areas.any(Province.id == province_id))
        
    # 3. Group by Worker to calculate aggregates correctly
    query = query.group_by(Worker.id)
    
    # 4. Apply Sorting
    if sort_by == 'rating_desc':
        query = query.order_by(db.desc('avg_rating'), db.desc('review_count'))
    elif sort_by == 'reviews_desc':
        query = query.order_by(db.desc('review_count'), db.desc('avg_rating'))
    elif sort_by == 'price_asc':
        query = query.order_by(Worker.starting_price.asc())
    else:
        query = query.order_by(Worker.experience.desc())
        
    results = query.all()
    
    # Fetch lists for page filters dropdowns
    categories = SkillCategory.query.order_by(SkillCategory.name).all()
    provinces = Province.query.order_by(Province.name).all()
    
    selected_skill = Skill.query.get(skill_id) if skill_id else None
    selected_province = Province.query.get(province_id) if province_id else None
    
    return render_template(
        'search_results.html',
        results=results,
        categories=categories,
        provinces=provinces,
        skill_id=skill_id,
        province_id=province_id,
        sort_by=sort_by,
        selected_skill=selected_skill,
        selected_province=selected_province
    )

# 7. Worker Profile Details & Reviews posting
@app.route('/worker/<int:worker_id>', methods=['GET', 'POST'])
def worker_detail(worker_id):
    worker = Worker.query.get_or_404(worker_id)
    
    # Calculate stats
    avg_rating = db.session.query(func.coalesce(func.avg(Review.rating), 0)).filter(Review.worker_id == worker.id).scalar()
    review_count = db.session.query(func.count(Review.id)).filter(Review.worker_id == worker.id).scalar()
    
    # Fetch reviews
    reviews = Review.query.filter_by(worker_id=worker.id).order_by(Review.created_at.desc()).all()
    
    # Check if current user can submit a review
    can_review = False
    has_reviewed = False
    
    if 'user_id' in session:
        # Check if the user is not the worker themselves and user is a general user (role == 'user')
        if session.get('role') == 'user' and session.get('user_id') != worker.id:
            existing_review = Review.query.filter_by(user_id=session['user_id'], worker_id=worker.id).first()
            if existing_review:
                has_reviewed = True
            else:
                can_review = True
                
    if request.method == 'POST':
        if not can_review:
            flash('คุณไม่ได้รับอนุญาตให้ส่งรีวิวสำหรับช่างคนนี้ หรือคุณเคยรีวิวช่างคนนี้แล้ว', 'danger')
            return redirect(url_for('worker_detail', worker_id=worker_id))
            
        rating = request.form.get('rating', type=int)
        comment = request.form.get('comment', '').strip()
        
        if not rating or rating < 1 or rating > 5:
            flash('กรุณาเลือกคะแนนประเมิน (1-5 ดาว)', 'danger')
            return redirect(url_for('worker_detail', worker_id=worker_id))
            
        try:
            new_review = Review(
                user_id=session['user_id'],
                worker_id=worker.id,
                rating=rating,
                comment=comment
            )
            db.session.add(new_review)
            db.session.commit()
            flash('ขอบคุณสำหรับคะแนนรีวิวของคุณ!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('เกิดข้อผิดพลาดในการบันทึกรีวิว (คุณอาจเคยให้รีวิวช่างคนนี้ไปแล้ว)', 'danger')
            
        return redirect(url_for('worker_detail', worker_id=worker.id))
        
    return render_template(
        'worker_detail.html',
        worker=worker,
        avg_rating=round(avg_rating, 1),
        review_count=review_count,
        reviews=reviews,
        can_review=can_review,
        has_reviewed=has_reviewed
    )

# ==========================================
# SEED DATABASE FUNCTION
# ==========================================
def seed_data():
    if SkillCategory.query.first() is not None:
        return
        
    print("Database is empty. Seeding initial categories, skills, provinces, and dummy workers...")
    
    # 1. Add Provinces with Region Grouping
    provinces_data = [
        # ภาคกลาง
        {"name": "กรุงเทพมหานคร", "region": "ภาคกลาง"},
        {"name": "นนทบุรี", "region": "ภาคกลาง"},
        {"name": "ปทุมธานี", "region": "ภาคกลาง"},
        {"name": "สมุทรปราการ", "region": "ภาคกลาง"},
        # ภาคเหนือ
        {"name": "เชียงใหม่", "region": "ภาคเหนือ"},
        {"name": "เชียงราย", "region": "ภาคเหนือ"},
        {"name": "ลำปาง", "region": "ภาคเหนือ"},
        # ภาคใต้
        {"name": "ภูเก็ต", "region": "ภาคใต้"},
        {"name": "สงขลา", "region": "ภาคใต้"},
        {"name": "สุราษฎร์ธานี", "region": "ภาคใต้"},
        # ภาคตะวันออก
        {"name": "ชลบุรี", "region": "ภาคตะวันออก"},
        {"name": "ระยอง", "region": "ภาคตะวันออก"},
        # ภาคตะวันตก
        {"name": "กาญจนบุรี", "region": "ภาคตะวันตก"},
        {"name": "ประจวบคีรีขันธ์", "region": "ภาคตะวันตก"},
        # ภาคตะวันออกเฉียงเหนือ
        {"name": "ขอนแก่น", "region": "ภาคตะวันออกเฉียงเหนือ"},
        {"name": "นครราชสีมา", "region": "ภาคตะวันออกเฉียงเหนือ"}
    ]
    for p_info in provinces_data:
        prov = Province(name=p_info["name"], region=p_info["region"])
        db.session.add(prov)
    db.session.commit()
    
    # 2. Add Skill Categories and Skills
    categories_data = {
        "งานช่างในบ้าน (Home Maintenance)": [
            "ช่างไฟ (Electrician)", 
            "ช่างประปา (Plumber)", 
            "ช่างแอร์ (Air Conditioner Repair)",
            "ช่างไม้ (Carpenter)",
            "ช่างทาสี (Painter)"
        ],
        "งานบริการทำความสะอาด (Cleaning & Housekeeping)": [
            "แม่บ้านทำความสะอาดทั่วไป (General Cleaning)",
            "บริการทำความสะอาดบิ๊กคลีนนิ่ง (Deep Cleaning)",
            "ซักเบาะ/โซฟา/พรม (Upholstery Cleaning)"
        ],
        "งานไอทีและอุปกรณ์อิเล็กทรอนิกส์ (IT & Electronics)": [
            "ช่างซ่อมคอมพิวเตอร์ (Computer Repair)",
            "ช่างติดตั้งกล้องวงจรปิด (CCTV Installation)",
            "ซ่อมโทรศัพท์มือถือ (Mobile Repair)"
        ],
        "งานบริการสุขภาพและความงาม (Beauty & Wellness)": [
            "ช่างตัดผม/เสริมสวย (Hairdresser/Stylist)",
            "หมอนวดแผนไทย (Thai Massage)",
            "ช่างทำเล็บ (Nail Artist)"
        ]
    }
    
    for cat_name, skill_names in categories_data.items():
        category = SkillCategory(name=cat_name)
        db.session.add(category)
        db.session.commit()
        
        for name in skill_names:
            skill = Skill(name=name, category_id=category.id)
            db.session.add(skill)
        db.session.commit()

    # 3. Add Dummy Users and Workers
    # Dummy admin
    admin = User(username="admin", fullname="ผู้ดูแลระบบสูงสุด", role="admin", phone="020000000")
    admin.set_password("admin123")
    db.session.add(admin)
    
    # Worker 1: Somchai
    w1_user = User(username="somchai", fullname="นายสมชาย บริการดี", role="worker", phone="0812345678")
    w1_user.set_password("123456")
    db.session.add(w1_user)
    db.session.commit()
    
    w1 = Worker(
        id=w1_user.id,
        experience=5,
        starting_price=350.0,
        bio="ช่างไฟและช่างประปาฝีมือดี ประสบการณ์กว่า 5 ปี ยินดีให้บริการแก้ไขงานซ่อมไฟ ไฟรั่ว ไฟช็อต ท่อตัน ก๊อกน้ำซึม และงานประปาทุกชนิด ซื่อสัตย์ ตรงเวลา ราคาเป็นกันเองครับ"
    )
    db.session.add(w1)
    w1.skills.extend(Skill.query.filter(Skill.name.in_(["ช่างไฟ (Electrician)", "ช่างประปา (Plumber)"])).all())
    w1.service_areas.extend(Province.query.filter(Province.name.in_(["กรุงเทพมหานคร", "นนทบุรี", "ปทุมธานี"])).all())
    
    # Worker 2: Somsri
    w2_user = User(username="somsri", fullname="นางสาวสมศรี สะอาดเอี่ยม", role="worker", phone="0823456789")
    w2_user.set_password("123456")
    db.session.add(w2_user)
    db.session.commit()
    
    w2 = Worker(
        id=w2_user.id,
        experience=3,
        starting_price=250.0,
        bio="บริการรับทำความสะอาดบ้าน คอนโด ออฟฟิศ ทั้งแบบรายวันและรายเดือน มั่นใจในเรื่องความสะอาด อุปกรณ์ทำความสะอาดและน้ำยาทำความสะอาดของทางเราปลอดภัย ได้มาตรฐาน มีประวัติการทำงานดีและผ่านการตรวจสอบประวัติอาชญากรรมเรียบร้อยค่ะ"
    )
    db.session.add(w2)
    w2.skills.extend(Skill.query.filter(Skill.name.in_(["แม่บ้านทำความสะอาดทั่วไป (General Cleaning)", "บริการทำความสะอาดบิ๊กคลีนนิ่ง (Deep Cleaning)"])).all())
    w2.service_areas.extend(Province.query.filter(Province.name.in_(["กรุงเทพมหานคร", "สมุทรปราการ"])).all())
    
    # Worker 3: Ekachai
    w3_user = User(username="ekachai", fullname="นายเอกชัย ไอทีโซลูชั่น", role="worker", phone="0834567890")
    w3_user.set_password("123456")
    db.session.add(w3_user)
    db.session.commit()
    
    w3 = Worker(
        id=w3_user.id,
        experience=8,
        starting_price=500.0,
        bio="รับซ่อมคอมพิวเตอร์ อัปเกรด แก้ไขปัญหาระบบอินเทอร์เน็ต ทั้งที่บ้านและสำนักงาน ติดตั้งระบบกล้องวงจรปิด CCTV แบรนด์ดัง บริการด่วนถึงที่ในเขตพื้นที่จังหวัดเชียงใหม่ ประสบการณ์ทำงานบริษัทไอทีใหญ่มากว่า 8 ปี"
    )
    db.session.add(w3)
    w3.skills.extend(Skill.query.filter(Skill.name.in_(["ช่างซ่อมคอมพิวเตอร์ (Computer Repair)", "ช่างติดตั้งกล้องวงจรปิด (CCTV Installation)"])).all())
    w3.service_areas.extend(Province.query.filter(Province.name.in_(["เชียงใหม่"])).all())
    
    # Worker 4: Anan (New)
    w4_user = User(username="anan", fullname="นายอนันต์ เย็นฉ่ำ", role="worker", phone="0845678901")
    w4_user.set_password("123456")
    db.session.add(w4_user)
    db.session.commit()
    
    w4 = Worker(
        id=w4_user.id,
        experience=6,
        starting_price=400.0,
        bio="ช่างแอร์ฝีมือดี บริการล้างแอร์บ้าน ซ่อมแอร์น้ำยารั่ว ล้างใหญ่ล้างย่อยราคาคุ้มค่า บริการตรงต่อเวลา รับประกันความเย็นหลังการบริการ 60 วัน ยินดีให้บริการในเขตกรุงเทพฯ และปทุมธานีครับ"
    )
    db.session.add(w4)
    w4.skills.extend(Skill.query.filter(Skill.name.in_(["ช่างแอร์ (Air Conditioner Repair)"])).all())
    w4.service_areas.extend(Province.query.filter(Province.name.in_(["กรุงเทพมหานคร", "ปทุมธานี"])).all())
    
    # Worker 5: Nipa (New)
    w5_user = User(username="nipa", fullname="นางสาวนิภา บิวตี้ซาลอน", role="worker", phone="0856789012")
    w5_user.set_password("123456")
    db.session.add(w5_user)
    db.session.commit()
    
    w5 = Worker(
        id=w5_user.id,
        experience=4,
        starting_price=300.0,
        bio="ช่างทำผมและทำเล็บนอกสถานที่ บริการตัดผมหญิง-ชาย ทำสี ดัดดิจิตอล และทำเล็บเจลสไตล์เกาหลี ใช้อุปกรณ์เกรดพรีเมียม สะอาด ปลอดภัย ยินดีให้บริการถึงบ้านในเขตนครหลวงค่ะ"
    )
    db.session.add(w5)
    w5.skills.extend(Skill.query.filter(Skill.name.in_(["ช่างตัดผม/เสริมสวย (Hairdresser/Stylist)", "ช่างทำเล็บ (Nail Artist)"])).all())
    w5.service_areas.extend(Province.query.filter(Province.name.in_(["กรุงเทพมหานคร", "นนทบุรี"])).all())
    
    # Worker 6: Veera (New)
    w6_user = User(username="veera", fullname="นายวีระ ซ่อมด่วน", role="worker", phone="0867890123")
    w6_user.set_password("123456")
    db.session.add(w6_user)
    db.session.commit()
    
    w6 = Worker(
        id=w6_user.id,
        experience=10,
        starting_price=600.0,
        bio="ช่างไม้โบราณและงานทาสีบ้าน บริการซ่อมแซมเฟอร์นิเจอร์ไม้ ตกแต่งบิวท์อิน ต่อเติมบ้านไม้โบราณ และทาสีปรับภูมิทัศน์ใหม่ งานละเอียด สวยงาม ฝีมือประณีต ประสบการณ์มากกว่า 10 ปี"
    )
    db.session.add(w6)
    w6.skills.extend(Skill.query.filter(Skill.name.in_(["ช่างไม้ (Carpenter)", "ช่างทาสี (Painter)"])).all())
    w6.service_areas.extend(Province.query.filter(Province.name.in_(["เชียงใหม่", "เชียงราย"])).all())
    
    # Worker 7: Chatchai (New)
    w7_user = User(username="chatchai", fullname="นายฉัตรชัย ติดกล้องวงจรปิด", role="worker", phone="0878901234")
    w7_user.set_password("123456")
    db.session.add(w7_user)
    db.session.commit()
    
    w7 = Worker(
        id=w7_user.id,
        experience=5,
        starting_price=450.0,
        bio="รับติดตั้งกล้องวงจรปิด CCTV แบรนด์ดัง พร้อมเซ็ตระบบออนไลน์ผ่านโทรศัพท์มือถือ และรับซ่อมโทรศัพท์มือถือสมาร์ทโฟนทุกยี่ห้อ (จอร้าว แบตเสื่อม ปัญหาซอฟต์แวร์) นอกสถานที่ บริการรวดเร็วทันใจ"
    )
    db.session.add(w7)
    w7.skills.extend(Skill.query.filter(Skill.name.in_(["ช่างติดตั้งกล้องวงจรปิด (CCTV Installation)", "ซ่อมโทรศัพท์มือถือ (Mobile Repair)"])).all())
    w7.service_areas.extend(Province.query.filter(Province.name.in_(["ภูเก็ต", "สงขลา", "สุราษฎร์ธานี"])).all())
    
    # Worker 8: Wilai (New)
    w8_user = User(username="wilai", fullname="นางวิไล นวดแผนโบราณ", role="worker", phone="0889012345")
    w8_user.set_password("123456")
    db.session.add(w8_user)
    db.session.commit()
    
    w8 = Worker(
        id=w8_user.id,
        experience=7,
        starting_price=350.0,
        bio="หมอนวดแผนไทยประยุกต์ มีใบอนุญาตวิชาชีพ นวดไทยแก้อาการ นวดแก้ออฟฟิศซินโดรม นวดฝ่าเท้า นวดอโรมานอกสถานที่เพื่อความผ่อนคลายและลดอาการเมื่อยล้า ยินดีบริการถึงบ้านหรือโรงแรมพักผ่อน"
    )
    db.session.add(w8)
    w8.skills.extend(Skill.query.filter(Skill.name.in_(["หมอนวดแผนไทย (Thai Massage)"])).all())
    w8.service_areas.extend(Province.query.filter(Province.name.in_(["ชลบุรี", "ระยอง"])).all())
    
    db.session.commit()
    
    # 4. Add Dummy Customers
    u1 = User(username="user1", fullname="สมยศ รักการเรียน", role="user", phone="0911112222")
    u1.set_password("123456")
    u2 = User(username="user2", fullname="พรทิพย์ สวยงาม", role="user", phone="0922223333")
    u2.set_password("123456")
    db.session.add_all([u1, u2])
    db.session.commit()
    
    # 5. Add Dummy Reviews
    rev1 = Review(user_id=u1.id, worker_id=w1.id, rating=5, comment="ช่างสมชายบริการดีมากๆ ครับ สุภาพ ทำงานเรียบร้อย รวดเร็ว หาจุดไฟรั่วได้แม่ยำมาก แนะนำเลยครับ")
    rev2 = Review(user_id=u2.id, worker_id=w1.id, rating=4, comment="ช่างมาตรงเวลาดีค่ะ งานเปลี่ยนสายก๊อกอ่างล้างจานเรียบร้อยดี ราคาเป็นกันเอง")
    rev3 = Review(user_id=u1.id, worker_id=w2.id, rating=5, comment="แม่บ้านสมศรีทำความสะอาดห้องสะอาดเนี้ยบมากๆ ซอกหลืบตู้เก็บเรียบร้อย มีกลิ่นหอมสะอาด คุ้มราคามากค่ะ")
    
    # New reviews for workers 4-8
    rev4 = Review(user_id=u1.id, worker_id=w4.id, rating=5, comment="ล้างแอร์สะอาดดีมาก ลมเย็นเจี๊ยบ ราคาไม่แพง ช่างบริการดี สุภาพมากครับ")
    rev5 = Review(user_id=u2.id, worker_id=w5.id, rating=4, comment="ช่างนิภาทำเล็บได้สวยถูกใจมากค่ะ ลวดลายเรียบหรูสีทนนานคุ้มราคา")
    rev6 = Review(user_id=u1.id, worker_id=w6.id, rating=5, comment="ช่างวีระซ่อมโต๊ะไม้เก่ากลับมาแข็งแรงสมบูรณ์ ฝีมือประณีตมากๆ ครับ")
    rev7 = Review(user_id=u2.id, worker_id=w7.id, rating=4, comment="ติดตั้งระบบกล้องวงจรปิด CCTV ได้รวดเร็ว เซ็ตเปิดดูผ่านแอปมือถือสะดวกมาก")
    rev8 = Review(user_id=u1.id, worker_id=w8.id, rating=5, comment="แก้อาการออฟฟิศซินโดรมปวดบ่าไหล่ดีมากเลยครับ นวดตรงจุด ปลอดภัย โล่งเลยครับ")
    
    db.session.add_all([rev1, rev2, rev3, rev4, rev5, rev6, rev7, rev8])
    db.session.commit()
    print("Database seeding completed successfully!")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
    # Run server
    app.run(debug=True, port=5000)
