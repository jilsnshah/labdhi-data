"""Seed realistic demo data so the whole workflow can be tried immediately.

Usage::

    python -m app.seed             # wipe demo tables and reseed
    python -m app.seed --if-empty  # only seed when the database has no users
    python -m app.seed --reset     # same as the default, explicit
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import (
    Activity,
    Application,
    AuditLog,
    CustomerInquiry,
    Grade,
    Inquiry,
    Location,
    Manufacturer,
    Material,
    Note,
    Party,
    PartyApplication,
    PartyLocation,
    PartyProduct,
    Product,
    SupplierInquiry,
    TransportInquiry,
    User,
)
from app.models.enums import (
    ActivityOutcome,
    ActivityStatus,
    ActivityType,
    AuditAction,
    InquiryStatus,
    InquiryType,
    LocationType,
    PartyProductRelationship,
    PartySource,
    PartyStage,
    PartyType,
    QuantityUnit,
    UserRole,
)

TABLES = [
    "audit_logs",
    "activities",
    "notes",
    "inquiry_responses",
    "transport_inquiries",
    "supplier_inquiries",
    "customer_inquiries",
    "inquiries",
    "party_products",
    "party_locations",
    "locations",
    "parties",
    "party_applications",
    "product_applications",
    "products",
    "grades",
    "materials",
    "manufacturers",
    "applications",
    "users",
]

NOW = datetime.now(UTC)
TODAY = NOW.date()

#: The trader's local day, so seeded "today 11:00" lands inside the business day.
BUSINESS_TZ = timezone(timedelta(minutes=settings.display_timezone_offset_minutes))
BUSINESS_TODAY = datetime.now(BUSINESS_TZ).date()


def _at(day_offset: int, hour: int, minute: int = 0) -> datetime:
    """A local business time, converted to UTC for storage."""
    local = datetime.combine(
        BUSINESS_TODAY + timedelta(days=day_offset),
        time(hour=hour, minute=minute),
        tzinfo=BUSINESS_TZ,
    )
    return local.astimezone(UTC)


def _ago(days: float = 0, hours: float = 0) -> datetime:
    return NOW - timedelta(days=days, hours=hours)


def _ahead(days: float = 0, hours: float = 0) -> datetime:
    return NOW + timedelta(days=days, hours=hours)


def reset(session: Session) -> None:
    session.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
    session.commit()


def log(
    session: Session,
    user: User,
    entity_type: str,
    entity_id: int,
    action: AuditAction,
    created_at: datetime,
    old: dict | None = None,
    new: dict | None = None,
) -> None:
    entry = AuditLog(
        user_id=user.id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_value=old,
        new_value=new,
    )
    session.add(entry)
    session.flush()
    entry.created_at = created_at


def seed(session: Session) -> dict[str, int]:
    # ---------------- users ----------------
    admin = User(
        name=settings.seed_admin_name,
        email=settings.seed_admin_email.lower(),
        password_hash=hash_password(settings.seed_admin_password),
        role=UserRole.ADMIN,
    )
    desk = User(
        name="Ravi Mehta",
        email="ravi@tradercrm.in",
        password_hash=hash_password("ravi123"),
        role=UserRole.USER,
    )
    rahul = User(
        name="Rahul Sharma",
        email="rahul@tradercrm.in",
        password_hash=hash_password("rahul123"),
        role=UserRole.SALESPERSON,
        phone="+91 98250 44001",
    )
    amit = User(
        name="Amit Patel",
        email="amit@tradercrm.in",
        password_hash=hash_password("amit123"),
        role=UserRole.SALESPERSON,
        phone="+91 98250 44002",
    )
    session.add_all([admin, desk, rahul, amit])
    session.flush()

    # ---------------- materials & grades ----------------
    materials = {
        name: Material(name=name, description=description)
        for name, description in [
            ("PVC", "Polyvinyl chloride suspension resin"),
            ("HDPE", "High density polyethylene"),
            ("PP", "Polypropylene homopolymer and copolymer"),
            ("LLDPE", "Linear low density polyethylene"),
            ("EVA", "Ethylene vinyl acetate"),
        ]
    }
    session.add_all(materials.values())
    session.flush()

    grade_specs = [
        ("PVC", "K-67", "General purpose pipe grade"),
        ("PVC", "K-65", "Profile and fittings grade"),
        ("PVC", "K-57", "Injection moulding grade"),
        ("HDPE", "MFI 0.3", "Blow moulding / pipe grade"),
        ("HDPE", "MFI 7", "Injection moulding grade"),
        ("PP", "MFI 12", "Raffia and injection moulding"),
        ("LLDPE", "Film 1", "Film extrusion grade"),
        ("EVA", "VA 18", "Footwear and hot melt adhesive"),
    ]
    grades = {
        (material_name, grade_name): Grade(
            material_id=materials[material_name].id, name=grade_name, description=description
        )
        for material_name, grade_name, description in grade_specs
    }
    session.add_all(grades.values())

    # ---------------- manufacturers ----------------
    manufacturers = {
        name: Manufacturer(name=name, code=code, description=description)
        for name, code, description in [
            ("Reliance", "RIL", "Reliance Industries Limited"),
            ("Finolex", "FNX", "Finolex Industries"),
            ("SABIC", "SBC", "Saudi Basic Industries Corporation"),
            ("IOCL", "IOC", "Indian Oil Corporation"),
            ("Haldia", "HPL", "Haldia Petrochemicals"),
        ]
    }
    session.add_all(manufacturers.values())

    # ---------------- applications ----------------
    applications = {
        name: Application(name=name, description=description)
        for name, description in [
            ("PVC Pipes", "Agricultural and plumbing pipes"),
            ("PVC Windows", "uPVC window and door profiles"),
            ("Profiles", "Extruded profile sections"),
            ("Injection Moulding", "Moulded fittings and housewares"),
            ("Packaging", "Films, bags and packaging"),
            ("Cable Insulation", "Wire and cable compounds"),
            ("Raffia", "Woven sacks and FIBC"),
        ]
    }
    session.add_all(applications.values())
    session.flush()

    # ---------------- products ----------------
    def product(
        material: str,
        grade: str,
        manufacturer: str,
        apps: list[str],
        description: str | None = None,
    ) -> Product:
        item = Product(
            material_id=materials[material].id,
            grade_id=grades[(material, grade)].id,
            manufacturer_id=manufacturers[manufacturer].id,
            display_name=f"{manufacturer} {material} {grade}",
            description=description,
        )
        item.applications = [applications[name] for name in apps]
        return item

    products = {
        "ril_pvc_k67": product(
            "PVC",
            "K-67",
            "Reliance",
            ["PVC Pipes", "PVC Windows", "Profiles"],
            "Workhorse pipe grade, highest demand",
        ),
        "fnx_pvc_k67": product("PVC", "K-67", "Finolex", ["PVC Pipes", "Profiles"]),
        "ril_pvc_k65": product("PVC", "K-65", "Reliance", ["Profiles", "PVC Windows"]),
        "hpl_pvc_k57": product("PVC", "K-57", "Haldia", ["Injection Moulding"]),
        "sabic_hdpe_03": product("HDPE", "MFI 0.3", "SABIC", ["PVC Pipes", "Packaging"]),
        "ril_hdpe_7": product("HDPE", "MFI 7", "Reliance", ["Injection Moulding"]),
        "iocl_pp_12": product("PP", "MFI 12", "IOCL", ["Raffia", "Injection Moulding"]),
        "ril_lldpe_film": product("LLDPE", "Film 1", "Reliance", ["Packaging"]),
        "ril_eva_18": product("EVA", "VA 18", "Reliance", ["Cable Insulation"]),
    }
    session.add_all(products.values())
    session.flush()

    # ---------------- locations ----------------
    def location(
        label: str,
        city: str,
        state: str,
        line1: str,
        pincode: str,
        coords: tuple[str, str] | None = None,
    ) -> Location:
        return Location(
            label=label,
            address_line_1=line1,
            city=city,
            state=state,
            country="India",
            pincode=pincode,
            latitude=Decimal(coords[0]) if coords else None,
            longitude=Decimal(coords[1]) if coords else None,
        )

    locations = {
        "abc_ho": location(
            "ABC Pipes Head Office",
            "Rajkot",
            "Gujarat",
            "Gondal Road",
            "360004",
            ("22.274500", "70.790000"),
        ),
        "abc_factory": location(
            "ABC Pipes Factory",
            "Rajkot",
            "Gujarat",
            "Shapar Veraval GIDC",
            "360024",
            ("22.173600", "70.869700"),
        ),
        "xyz_ho": location(
            "XYZ Polymers Office",
            "Ahmedabad",
            "Gujarat",
            "CG Road",
            "380009",
            ("23.027500", "72.558100"),
        ),
        "xyz_plant": location(
            "XYZ Polymers Plant",
            "Sanand",
            "Gujarat",
            "Sanand GIDC Phase 2",
            "382110",
            ("22.989200", "72.382400"),
        ),
        "shreeji_ho": location(
            "Shreeji Profiles",
            "Surat",
            "Gujarat",
            "Udhna Magdalla Road",
            "395017",
            ("21.159300", "72.783200"),
        ),
        "kiran_ho": location(
            "Kiran Moulders",
            "Vadodara",
            "Gujarat",
            "Makarpura GIDC",
            "390010",
            ("22.262700", "73.187500"),
        ),
        "deep_ho": location(
            "Deepak Packaging",
            "Indore",
            "Madhya Pradesh",
            "Sanwer Road",
            "452015",
            ("22.772100", "75.857700"),
        ),
        "sup_mumbai": location(
            "Mahavir Polymers Office", "Mumbai", "Maharashtra", "Masjid Bunder", "400009"
        ),
        "sup_ahm_wh": location(
            "Mahavir Ahmedabad Warehouse",
            "Ahmedabad",
            "Gujarat",
            "Narol Circle",
            "382405",
            ("22.972400", "72.601700"),
        ),
        "sup_del": location(
            "Shakti Traders", "Delhi", "Delhi", "Naraina Industrial Area", "110028"
        ),
        "sup_vapi": location("Western Polychem", "Vapi", "Gujarat", "GIDC Char Rasta", "396195"),
        "sup_kandla": location(
            "Oceanic Imports Warehouse", "Gandhidham", "Gujarat", "Kandla SEZ", "370230"
        ),
        "trn_rjk": location("Jay Transport Yard", "Rajkot", "Gujarat", "Bhavnagar Road", "360003"),
        "trn_ahm": location("Shree Logistics Hub", "Ahmedabad", "Gujarat", "Aslali", "382427"),
        "trn_sur": location("Patel Roadways Depot", "Surat", "Gujarat", "Katargam", "395004"),
    }
    session.add_all(locations.values())
    session.flush()

    # ---------------- parties ----------------
    def party(
        name: str,
        party_type: PartyType,
        contact: str,
        phone: str,
        email: str,
        gst: str,
        notes: str | None = None,
    ) -> Party:
        return Party(
            name=name,
            party_type=party_type,
            contact_person=contact,
            phone=phone,
            email=email,
            gst_number=gst,
            notes=notes,
        )

    parties = {
        "abc": party(
            "ABC Pipes",
            PartyType.CUSTOMER,
            "Jignesh Patel",
            "+91 98250 11001",
            "purchase@abcpipes.in",
            "24AABCA1234A1Z5",
            "Buys 150-200 MT PVC per month.",
        ),
        "xyz": party(
            "XYZ Polymers",
            PartyType.CUSTOMER,
            "Nilesh Shah",
            "+91 98250 11002",
            "nilesh@xyzpoly.in",
            "24AABCX5678B1Z2",
        ),
        "shreeji": party(
            "Shreeji Profiles",
            PartyType.CUSTOMER,
            "Hardik Desai",
            "+91 98250 11003",
            "hardik@shreejiprofiles.in",
            "24AABCS9012C1Z8",
        ),
        "kiran": party(
            "Kiran Moulders",
            PartyType.CUSTOMER,
            "Amit Joshi",
            "+91 98250 11004",
            "amit@kiranmoulders.in",
            "24AABCK3456D1Z1",
        ),
        "deepak": party(
            "Deepak Packaging",
            PartyType.CUSTOMER,
            "Rohit Agarwal",
            "+91 98250 11005",
            "rohit@deepakpack.in",
            "23AABCD7890E1Z4",
        ),
        "mahavir": party(
            "Mahavir Polymers",
            PartyType.SUPPLIER,
            "Sanjay Jain",
            "+91 98200 22001",
            "sales@mahavirpoly.in",
            "27AABCM1234F1Z9",
            "Reliance authorised distributor.",
        ),
        "shakti": party(
            "Shakti Traders",
            PartyType.SUPPLIER,
            "Vikram Singh",
            "+91 98100 22002",
            "vikram@shaktitraders.in",
            "07AABCS5678G1Z6",
        ),
        "western": party(
            "Western Polychem",
            PartyType.SUPPLIER,
            "Paresh Mehta",
            "+91 98250 22003",
            "paresh@westernpolychem.in",
            "24AABCW9012H1Z3",
        ),
        "oceanic": party(
            "Oceanic Imports",
            PartyType.SUPPLIER,
            "Farhan Qureshi",
            "+91 98790 22004",
            "farhan@oceanicimports.in",
            "24AABCO3456I1Z7",
            "Imported SABIC material, Kandla.",
        ),
        "jay": party(
            "Jay Transport",
            PartyType.TRANSPORTER,
            "Bharat Vala",
            "+91 98250 33001",
            "dispatch@jaytransport.in",
            "24AABCJ1234J1Z2",
            "Rajkot - Saurashtra routes.",
        ),
        "shree_log": party(
            "Shree Logistics",
            PartyType.TRANSPORTER,
            "Manish Thakkar",
            "+91 98250 33002",
            "ops@shreelogistics.in",
            "24AABCL5678K1Z5",
        ),
        "patel_road": party(
            "Patel Roadways",
            PartyType.TRANSPORTER,
            "Dinesh Patel",
            "+91 98250 33003",
            "booking@patelroadways.in",
            "24AABCP9012L1Z8",
        ),
    }
    session.add_all(parties.values())
    session.flush()

    def link_location(
        party_key: str, location_key: str, location_type: LocationType, primary: bool = False
    ) -> None:
        session.add(
            PartyLocation(
                party_id=parties[party_key].id,
                location_id=locations[location_key].id,
                location_type=location_type,
                is_primary=primary,
            )
        )

    link_location("abc", "abc_ho", LocationType.HEAD_OFFICE, True)
    link_location("abc", "abc_factory", LocationType.FACTORY)
    link_location("xyz", "xyz_ho", LocationType.HEAD_OFFICE, True)
    link_location("xyz", "xyz_plant", LocationType.FACTORY)
    link_location("shreeji", "shreeji_ho", LocationType.FACTORY, True)
    link_location("kiran", "kiran_ho", LocationType.FACTORY, True)
    link_location("deepak", "deep_ho", LocationType.FACTORY, True)
    link_location("mahavir", "sup_mumbai", LocationType.HEAD_OFFICE, True)
    link_location("mahavir", "sup_ahm_wh", LocationType.WAREHOUSE)
    link_location("shakti", "sup_del", LocationType.HEAD_OFFICE, True)
    link_location("western", "sup_vapi", LocationType.WAREHOUSE, True)
    link_location("oceanic", "sup_kandla", LocationType.WAREHOUSE, True)
    link_location("jay", "trn_rjk", LocationType.HEAD_OFFICE, True)
    link_location("shree_log", "trn_ahm", LocationType.HEAD_OFFICE, True)
    link_location("patel_road", "trn_sur", LocationType.HEAD_OFFICE, True)

    def link_product(
        party_key: str,
        product_key: str,
        relationship: PartyProductRelationship,
        notes: str | None = None,
    ) -> None:
        session.add(
            PartyProduct(
                party_id=parties[party_key].id,
                product_id=products[product_key].id,
                relationship_type=relationship,
                notes=notes,
            )
        )

    purchases = PartyProductRelationship.PURCHASES
    interested = PartyProductRelationship.INTERESTED_IN
    supplies = PartyProductRelationship.SUPPLIES

    link_product("abc", "ril_pvc_k67", purchases, "Regular 100 MT/month")
    link_product("abc", "fnx_pvc_k67", purchases, "Alternate source")
    link_product("abc", "ril_pvc_k65", interested)
    link_product("xyz", "ril_pvc_k67", purchases)
    link_product("xyz", "sabic_hdpe_03", purchases)
    link_product("xyz", "ril_lldpe_film", interested)
    link_product("shreeji", "ril_pvc_k65", purchases, "Window profile line")
    link_product("shreeji", "ril_pvc_k67", interested)
    link_product("kiran", "hpl_pvc_k57", purchases)
    link_product("kiran", "ril_hdpe_7", purchases)
    link_product("deepak", "ril_lldpe_film", purchases)
    link_product("deepak", "iocl_pp_12", interested)

    link_product("mahavir", "ril_pvc_k67", supplies, "Ex-Ahmedabad warehouse stock")
    link_product("mahavir", "ril_pvc_k65", supplies)
    link_product("mahavir", "ril_lldpe_film", supplies)
    link_product("shakti", "ril_pvc_k67", supplies, "Ex-Delhi, higher freight")
    link_product("shakti", "fnx_pvc_k67", supplies)
    link_product("western", "fnx_pvc_k67", supplies)
    link_product("western", "hpl_pvc_k57", supplies)
    link_product("western", "iocl_pp_12", supplies)
    link_product("oceanic", "sabic_hdpe_03", supplies, "Import stock at Kandla")
    link_product("oceanic", "ril_pvc_k67", supplies)
    session.flush()

    # ---------------- party applications ----------------
    # What line of business each party is in, as distinct from what they have
    # traded with us. A fabricator who has never bought from us is still the
    # right call for a pipes grade if pipes are what they make.
    def link_application(party_key: str, *application_names: str) -> None:
        for name in application_names:
            session.add(
                PartyApplication(
                    party_id=parties[party_key].id,
                    application_id=applications[name].id,
                )
            )

    link_application("abc", "PVC Pipes")
    link_application("xyz", "PVC Pipes", "Packaging")
    link_application("shreeji", "PVC Windows", "Profiles")
    link_application("kiran", "Injection Moulding")
    link_application("deepak", "Packaging", "Raffia")

    link_application("mahavir", "PVC Pipes", "PVC Windows", "Profiles")
    link_application("shakti", "PVC Pipes", "Profiles")
    link_application("western", "PVC Windows", "Profiles", "Cable Insulation")
    link_application("oceanic", "Packaging", "Injection Moulding")
    session.flush()

    # ---------------- inquiries ----------------
    # Recorded quotations: who, what, how much, where, and the rate. Supplier and
    # customer rates are rupees per kilogram; transport prices are rupees.
    def inquiry(
        inquiry_type: InquiryType,
        created: datetime,
        *,
        closed: datetime | None = None,
        creator: User | None = None,
    ) -> Inquiry:
        author = creator or desk
        header = Inquiry(
            inquiry_type=inquiry_type,
            status=InquiryStatus.CLOSED if closed else InquiryStatus.ACTIVE,
            created_by=author.id,
            closed_at=closed,
            closed_by=author.id if closed else None,
        )
        session.add(header)
        session.flush()
        header.created_at = created
        header.updated_at = closed or created
        log(
            session,
            author,
            "inquiry",
            header.id,
            AuditAction.CREATE,
            created,
            new={"inquiry_type": inquiry_type.value, "status": InquiryStatus.ACTIVE.value},
        )
        if closed:
            log(
                session,
                author,
                "inquiry",
                header.id,
                AuditAction.STATUS_CHANGE,
                closed,
                old={"status": InquiryStatus.ACTIVE.value},
                new={"status": InquiryStatus.CLOSED.value},
            )
        return header

    def customer_quote(
        party_key: str,
        product_key: str,
        quantity: str,
        location_key: str | None,
        rate: str | None,
        created: datetime,
        closed: datetime | None = None,
    ) -> Inquiry:
        header = inquiry(InquiryType.CUSTOMER, created, closed=closed)
        session.add(
            CustomerInquiry(
                inquiry_id=header.id,
                customer_id=parties[party_key].id,
                product_id=products[product_key].id,
                quantity=Decimal(quantity),
                unit=QuantityUnit.MT,
                location_id=locations[location_key].id if location_key else None,
                rate=Decimal(rate) if rate else None,
            )
        )
        session.flush()
        return header

    def supplier_quote(
        party_key: str,
        product_key: str,
        quantity: str,
        location_key: str | None,
        rate: str | None,
        created: datetime,
        closed: datetime | None = None,
    ) -> Inquiry:
        header = inquiry(InquiryType.SUPPLIER, created, closed=closed)
        session.add(
            SupplierInquiry(
                inquiry_id=header.id,
                supplier_id=parties[party_key].id,
                product_id=products[product_key].id,
                quantity=Decimal(quantity),
                unit=QuantityUnit.MT,
                location_id=locations[location_key].id if location_key else None,
                rate=Decimal(rate) if rate else None,
            )
        )
        session.flush()
        return header

    def transport_quote(
        party_key: str,
        quantity: str,
        pickup_key: str,
        drop_key: str,
        price: str | None,
        created: datetime,
        closed: datetime | None = None,
    ) -> Inquiry:
        header = inquiry(InquiryType.TRANSPORT, created, closed=closed)
        session.add(
            TransportInquiry(
                inquiry_id=header.id,
                transporter_id=parties[party_key].id,
                quantity=Decimal(quantity),
                unit=QuantityUnit.MT,
                pickup_location_id=locations[pickup_key].id,
                delivery_location_id=locations[drop_key].id,
                price=Decimal(price) if price else None,
            )
        )
        session.flush()
        return header

    # Customers: what they asked for and the rate quoted to them.
    ci1 = customer_quote("abc", "ril_pvc_k67", "20", "abc_factory", "92.50", _ago(days=3, hours=6))
    ci2 = customer_quote("shreeji", "ril_pvc_k65", "10", "shreeji_ho", None, _ago(hours=5))
    customer_quote("deepak", "ril_lldpe_film", "12", "deep_ho", "101.25", _ago(days=1, hours=3))
    customer_quote("xyz", "sabic_hdpe_03", "15", "xyz_plant", "106.00", _ago(days=12), _ago(days=9))
    customer_quote("kiran", "hpl_pvc_k57", "8", "kiran_ho", "88.00", _ago(days=20), _ago(days=17))

    # Suppliers: what they offered, from where, at what rate.
    supplier_quote("mahavir", "ril_pvc_k67", "25", "sup_ahm_wh", "90.80", _ago(days=2, hours=20))
    supplier_quote("shakti", "ril_pvc_k67", "20", "sup_del", "91.20", _ago(days=2, hours=18))
    supplier_quote("oceanic", "sabic_hdpe_03", "40", "sup_kandla", "103.50", _ago(days=4, hours=2))
    supplier_quote("mahavir", "ril_lldpe_film", "30", "sup_mumbai", "98.40", _ago(days=1))
    supplier_quote("western", "fnx_pvc_k67", "15", "sup_vapi", "89.90", _ago(days=10), _ago(days=8))
    supplier_quote("western", "iocl_pp_12", "18", "sup_vapi", "96.00", _ago(days=18), _ago(days=15))

    # Transporters: the route and the freight they quoted.
    transport_quote("jay", "20", "sup_ahm_wh", "abc_factory", "18000", _ago(days=2, hours=10))
    transport_quote("patel_road", "10", "trn_sur", "shreeji_ho", None, _ago(hours=4))
    transport_quote(
        "shree_log", "15", "sup_kandla", "xyz_plant", "26500", _ago(days=11), _ago(days=9)
    )

    # ---------------- activities (customers only) ----------------
    def activity(
        party_key: str,
        activity_type: ActivityType,
        status: ActivityStatus,
        creator: User,
        *,
        scheduled: datetime | None = None,
        completed: datetime | None = None,
        subject: str | None = None,
        note: str | None = None,
        outcome: str | None = None,
        parent: Activity | None = None,
        inquiry: Inquiry | None = None,
        created: datetime | None = None,
        assigned_to: User | None = None,
        location_key: str | None = None,
        outcome_code: ActivityOutcome | None = None,
    ) -> Activity:
        location = locations[location_key] if location_key else None
        row = Activity(
            party_id=parties[party_key].id,
            activity_type=activity_type,
            status=status,
            subject=subject,
            scheduled_at=scheduled,
            started_at=scheduled if completed else None,
            completed_at=completed,
            note=note,
            outcome=outcome,
            outcome_code=(
                outcome_code if outcome_code else (ActivityOutcome.COMPLETED if completed else None)
            ),
            parent_activity_id=parent.id if parent else None,
            related_inquiry_id=inquiry.id if inquiry else None,
            created_by=creator.id,
            completed_by=(assigned_to or creator).id if completed else None,
            assigned_salesperson_id=assigned_to.id if assigned_to else None,
            location_id=location.id if location else None,
            location_snapshot=(
                {
                    "location_id": location.id,
                    "label": location.label,
                    "address_line_1": location.address_line_1,
                    "address_line_2": location.address_line_2,
                    "city": location.city,
                    "state": location.state,
                    "country": location.country,
                    "pincode": location.pincode,
                    "latitude": str(location.latitude) if location.latitude else None,
                    "longitude": str(location.longitude) if location.longitude else None,
                }
                if location
                else None
            ),
        )
        session.add(row)
        session.flush()
        row.created_at = created or scheduled or completed or NOW
        return row

    call1 = activity(
        "abc",
        ActivityType.CALL,
        ActivityStatus.COMPLETED,
        desk,
        scheduled=_ago(days=3, hours=7),
        completed=_ago(days=3, hours=6),
        subject="Confirm PVC K-67 requirement",
        note="Customer messaged about PVC availability - call to confirm quantity and date.",
        outcome="Needs 20 MT by next week at Shapar factory. Target 91/kg.",
        inquiry=ci1,
    )
    followup1 = activity(
        "abc",
        ActivityType.CALL,
        ActivityStatus.COMPLETED,
        desk,
        scheduled=_ago(days=2, hours=10),
        completed=_ago(days=2, hours=9),
        subject="Share supplier rates",
        note="Share best supplier rate and close the order.",
        outcome="Customer asked for a lower rate; wants 91000 landed. Negotiating.",
        parent=call1,
        inquiry=ci1,
    )
    activity(
        "abc",
        ActivityType.CALL,
        ActivityStatus.SCHEDULED,
        desk,
        scheduled=_ahead(hours=3),
        subject="Final price negotiation",
        note="Offer 92500 landed and try to close 20 MT today.",
        parent=followup1,
        inquiry=ci1,
        created=_ago(days=2, hours=9),
    )
    activity(
        "abc",
        ActivityType.WHATSAPP,
        ActivityStatus.COMPLETED,
        desk,
        scheduled=_ago(days=1, hours=4),
        completed=_ago(days=1, hours=4),
        subject="Daily PVC price update",
        note="Sent today's PVC market price update.",
        outcome="Customer read the update and asked about K-65 as well.",
    )
    activity(
        "shreeji",
        ActivityType.VISIT,
        ActivityStatus.SCHEDULED,
        desk,
        scheduled=_at(5, 14, 0),
        subject="Discuss Q4 requirements",
        note="Visit the Surat plant to discuss the window profile line and Q4 volumes.",
        inquiry=ci2,
        created=_ago(hours=4),
        assigned_to=amit,
        location_key="shreeji_ho",
    )
    activity(
        "xyz",
        ActivityType.VISIT,
        ActivityStatus.COMPLETED,
        admin,
        scheduled=_ago(days=14, hours=6),
        completed=_ago(days=14, hours=4),
        subject="Plant visit after HDPE delivery",
        note="Review the 50 MT HDPE delivery and discuss the next lot.",
        outcome="Delivery accepted. Expects 50 MT HDPE every month from November.",
        assigned_to=rahul,
        location_key="xyz_plant",
        outcome_code=ActivityOutcome.CUSTOMER_INTERESTED,
    )
    activity(
        "xyz",
        ActivityType.CALL,
        ActivityStatus.SCHEDULED,
        admin,
        scheduled=_ago(days=1, hours=6),
        subject="November allocation",
        note="Overdue: confirm the November HDPE allocation.",
        created=_ago(days=5),
    )
    activity(
        "kiran",
        ActivityType.SMS,
        ActivityStatus.COMPLETED,
        desk,
        scheduled=_ago(days=7, hours=2),
        completed=_ago(days=7, hours=2),
        subject="Rate revision intimation",
        note="Sent the revised PVC K-57 rate by SMS.",
        outcome="No reply; customer had already closed the requirement.",
    )
    activity(
        "deepak",
        ActivityType.CALL,
        ActivityStatus.SCHEDULED,
        desk,
        scheduled=_ahead(days=2, hours=1),
        subject="LLDPE requirement follow-up",
        note="Check the LLDPE film requirement for next month.",
        created=_ago(days=1),
    )
    activity(
        "kiran",
        ActivityType.CALL,
        ActivityStatus.CANCELLED,
        desk,
        scheduled=_ago(days=4),
        subject="Follow up on K-57 pricing",
        note="Planned follow-up; cancelled because the inquiry was already closed.",
        created=_ago(days=6),
    )

    # ---------------- field work assigned to salespeople ----------------
    # Rahul's day: a morning visit, an afternoon call, an evening WhatsApp.
    rahul_visit = activity(
        "abc",
        ActivityType.VISIT,
        ActivityStatus.SCHEDULED,
        admin,
        scheduled=_at(0, 11, 0),
        subject="Visit ABC Pipes factory",
        note="Discuss the monthly PVC requirement. Customer is interested in Reliance K-67 - "
        "ask about the October quantity.",
        inquiry=ci1,
        created=_ago(days=1),
        assigned_to=rahul,
        location_key="abc_factory",
    )
    activity(
        "xyz",
        ActivityType.CALL,
        ActivityStatus.SCHEDULED,
        admin,
        scheduled=_at(0, 15, 0),
        subject="Call XYZ Polymers",
        note="Confirm the November HDPE allocation and the expected quantity.",
        created=_ago(days=1),
        assigned_to=rahul,
    )
    activity(
        "deepak",
        ActivityType.WHATSAPP,
        ActivityStatus.SCHEDULED,
        admin,
        scheduled=_at(0, 17, 0),
        subject="Send LLDPE price update",
        note="Share today's LLDPE film price and ask for next month's requirement.",
        created=_ago(days=1),
        assigned_to=rahul,
    )
    # Amit's day: one visit.
    activity(
        "kiran",
        ActivityType.VISIT,
        ActivityStatus.SCHEDULED,
        admin,
        scheduled=_at(0, 12, 0),
        subject="Visit Kiran Moulders",
        note="Show the Haldia K-57 sample and discuss the moulding requirement.",
        created=_ago(days=1),
        assigned_to=amit,
        location_key="kiran_ho",
    )
    # Rahul's upcoming work.
    activity(
        "abc",
        ActivityType.CALL,
        ActivityStatus.SCHEDULED,
        admin,
        scheduled=_at(2, 16, 0),
        subject="Follow up on the PVC quotation",
        note="Call after the quotation is shared.",
        inquiry=ci1,
        created=_ago(hours=6),
        assigned_to=rahul,
    )
    activity(
        "deepak",
        ActivityType.VISIT,
        ActivityStatus.SCHEDULED,
        admin,
        scheduled=_at(3, 11, 30),
        subject="Visit Deepak Packaging",
        note="Discuss the LLDPE film requirement for the new line.",
        created=_ago(hours=6),
        assigned_to=rahul,
        location_key="deep_ho",
    )
    # Something Rahul already finished, with the follow-up it produced.
    done_visit = activity(
        "abc",
        ActivityType.VISIT,
        ActivityStatus.COMPLETED,
        admin,
        scheduled=_at(-4, 11, 0),
        completed=_at(-4, 11, 47),
        subject="Visit ABC Pipes factory",
        note="Introduce the Reliance K-67 offer and check the October requirement.",
        outcome="Customer wants a quotation for 30 MT. Expects to confirm next week.",
        outcome_code=ActivityOutcome.FOLLOW_UP_REQUIRED,
        inquiry=ci1,
        created=_at(-6, 10, 0),
        assigned_to=rahul,
        location_key="abc_factory",
    )
    activity(
        "abc",
        ActivityType.CALL,
        ActivityStatus.COMPLETED,
        admin,
        scheduled=_at(-2, 16, 0),
        completed=_at(-2, 16, 12),
        subject="Quotation follow-up",
        note="Call the customer about the 30 MT quotation.",
        outcome="Customer asked for a better rate; negotiating with suppliers.",
        outcome_code=ActivityOutcome.FOLLOW_UP_REQUIRED,
        parent=done_visit,
        inquiry=ci1,
        created=_at(-4, 12, 0),
        assigned_to=rahul,
    )
    # An unassigned desk activity - the office handles this one itself.
    activity(
        "shreeji",
        ActivityType.CALL,
        ActivityStatus.SCHEDULED,
        desk,
        scheduled=_at(1, 10, 30),
        subject="Confirm K-65 trial feedback",
        note="Desk call, not assigned to the field team.",
        created=_ago(hours=3),
    )

    # ---------------- unknown parties (walk-ins and cold contacts) ----------------
    # Created the way the app creates them: one step, from an inquiry or a call.
    prospects = {
        "patel": Party(
            name="Patel Traders",
            party_type=PartyType.CUSTOMER,
            contact_person="Mahesh Patel",
            phone="+91 99250 77001",
            stage=PartyStage.PROSPECT,
            source=PartySource.QUICK_CREATE,
            notes="Walked in asking for PVC K-67 rates. No GST shared yet.",
        ),
        "unknown_caller": Party(
            name="+91 97250 88002",
            party_type=PartyType.CUSTOMER,
            phone="+91 97250 88002",
            stage=PartyStage.PROSPECT,
            source=PartySource.QUICK_CREATE,
            notes="Cold call, would not give a company name.",
        ),
        "nova": Party(
            name="Nova Polymers",
            party_type=PartyType.SUPPLIER,
            contact_person="Imran Shaikh",
            phone="+91 98330 55003",
            stage=PartyStage.PROSPECT,
            source=PartySource.QUICK_CREATE,
            notes="Name came up in a broker group; claims HDPE at Mundra.",
        ),
    }
    session.add_all(prospects.values())
    session.flush()

    # A prospect with no trading history at all, but a known line of business:
    # exactly the lead a product-only search would never surface.
    for application_name in ("PVC Pipes", "Packaging"):
        session.add(
            PartyApplication(
                party_id=prospects["nova"].id,
                application_id=applications[application_name].id,
            )
        )
    session.flush()

    # A prospect inquiry: the walk-in who wanted a K-67 rate.
    walk_in = inquiry(InquiryType.CUSTOMER, _ago(hours=2))
    session.add(
        CustomerInquiry(
            inquiry_id=walk_in.id,
            customer_id=prospects["patel"].id,
            product_id=products["ril_pvc_k67"].id,
            quantity=Decimal("5"),
            unit=QuantityUnit.MT,
            rate=Decimal("93.00"),
        )
    )
    session.flush()

    # Activities on non-customer parties are allowed now: a cold supplier call...
    cold_call = Activity(
        party_id=prospects["nova"].id,
        activity_type=ActivityType.CALL,
        status=ActivityStatus.SCHEDULED,
        subject="Cold call Nova Polymers",
        note="Check whether they really have HDPE at Mundra, and on what terms.",
        scheduled_at=_at(0, 16, 30),
        created_by=desk.id,
        assigned_salesperson_id=rahul.id,
    )
    session.add(cold_call)
    # ...and a visit to an address we only know as text.
    text_visit = Activity(
        party_id=prospects["patel"].id,
        activity_type=ActivityType.VISIT,
        status=ActivityStatus.SCHEDULED,
        subject="Visit Patel Traders shop",
        note="He said his shop is on Gondal Road, opposite the bus stand. Get the pin.",
        scheduled_at=_at(1, 12, 0),
        created_by=desk.id,
        assigned_salesperson_id=rahul.id,
        location_snapshot={
            "label": "Shop on Gondal Road, opposite the bus stand",
            "city": "Rajkot",
        },
    )
    session.add(text_visit)
    session.flush()
    text_visit.created_at = _ago(hours=2)
    cold_call.created_at = _ago(hours=2)

    # ---------------- notes ----------------
    note_specs = [
        (
            "abc",
            "Customer is expanding a second factory at Shapar. Expected requirement to "
            "increase from November.",
            desk,
            _ago(days=6),
        ),
        (
            "abc",
            "Prefers 15 days PDC. Payment record is clean for the last 8 months.",
            admin,
            _ago(days=20),
        ),
        (
            "xyz",
            "Plant runs two pipe extrusion lines; HDPE consumption around 50 MT/month.",
            admin,
            _ago(days=13),
        ),
        (
            "shreeji",
            "Evaluating uPVC window profiles; may need K-65 regularly from Q4.",
            desk,
            _ago(days=2),
        ),
        (
            "mahavir",
            "Reliance authorised distributor - best rates on K-67 ex-Ahmedabad.",
            desk,
            _ago(days=11),
        ),
        (
            "oceanic",
            "Import stock at Kandla; good for HDPE but payment terms are tight.",
            admin,
            _ago(days=16),
        ),
        (
            "jay",
            "Reliable for Saurashtra routes; 20 MT closed body trucks available same day.",
            desk,
            _ago(days=2, hours=12),
        ),
    ]
    for party_key, text_value, creator, created in note_specs:
        row = Note(party_id=parties[party_key].id, note=text_value, created_by=creator.id)
        session.add(row)
        session.flush()
        row.created_at = created
        row.updated_at = created

    session.commit()

    _ = rahul_visit  # kept for readability of the demo story above

    return {
        "users": 4,
        "materials": len(materials),
        "grades": len(grades),
        "manufacturers": len(manufacturers),
        "applications": len(applications),
        "party_applications": session.query(PartyApplication).count(),
        "products": len(products),
        "locations": len(locations),
        "parties": len(parties) + len(prospects),
        "prospects": len(prospects),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed demo data for the Trader CRM")
    parser.add_argument(
        "--if-empty", action="store_true", help="Do nothing when data already exists"
    )
    parser.add_argument(
        "--reset", action="store_true", help="Truncate existing data first (default)"
    )
    args = parser.parse_args(argv)

    with SessionLocal() as session:
        existing = session.scalar(select(User.id).limit(1))
        if existing is not None:
            if args.if_empty:
                print("Database already contains data - skipping seed.")
                return 0
            reset(session)
        counts = seed(session)

    print("Seeded demo data:")
    for key, value in counts.items():
        print(f"  {key:>14}: {value}")
    print(f"\nSign in with {settings.seed_admin_email} / {settings.seed_admin_password}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
