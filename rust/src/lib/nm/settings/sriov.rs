use crate::nm::nm_dbus::{
    NmConnection, NmSettingSriovVf, NmSettingSriovVfVlan,
};
use crate::{EthernetInterface, SrIovVfConfig};

pub(crate) fn gen_nm_sriov_setting(
    iface: &EthernetInterface,
    nm_conn: &mut NmConnection,
) {
    let sriov_conf = match iface
        .ethernet
        .as_ref()
        .and_then(|eth_conf| eth_conf.sr_iov.as_ref())
    {
        Some(c) => c,
        None => return,
    };

    if sriov_conf.total_vfs == Some(0) {
        nm_conn.sriov = None;
        return;
    }

    let mut nm_sriov_set = nm_conn.sriov.as_ref().cloned().unwrap_or_default();

    if let Some(v) = sriov_conf.total_vfs {
        nm_sriov_set.total_vfs = Some(v);
    }

    if let Some(autoprobe) = sriov_conf.drivers_autoprobe {
        nm_sriov_set.autoprobe_drivers = Some(autoprobe);
    }

    if let Some(vfs) = &sriov_conf.vfs {
        nm_sriov_set.vfs = Some(gen_nm_vfs(
            vfs,
            nm_sriov_set.vfs.as_ref().cloned().unwrap_or_default(),
        ));
    }

    nm_conn.sriov = Some(nm_sriov_set);
}

fn gen_nm_vfs(
    vfs: &[SrIovVfConfig],
    exist_nm_sriov_sets: Vec<NmSettingSriovVf>,
) -> Vec<NmSettingSriovVf> {
    let mut ret = Vec::with_capacity(vfs.len());
    for (i, vf) in vfs.iter().enumerate() {
        let mut nm_vf =
            if let Some(exist_nm_sriov_set) = exist_nm_sriov_sets.get(i) {
                exist_nm_sriov_set.clone()
            } else {
                NmSettingSriovVf::default()
            };
        nm_vf.index = Some(vf.id);
        if let Some(v) = &vf.mac_address {
            nm_vf.mac = Some(v.to_string());
        }
        if let Some(v) = vf.spoof_check {
            nm_vf.spoof_check = Some(v);
        }
        if let Some(v) = vf.trust {
            nm_vf.trust = Some(v);
        }
        if let Some(v) = vf.min_tx_rate {
            nm_vf.min_tx_rate = Some(v);
        }
        if let Some(v) = vf.max_tx_rate {
            nm_vf.max_tx_rate = Some(v);
        }
        if let Some(v) = vf.vlan_id {
            let mut nm_vf_vlan = NmSettingSriovVfVlan::default();
            nm_vf_vlan.id = v;
            nm_vf_vlan.qos = vf.qos.unwrap_or_default();
            nm_vf_vlan.protocol = vf.vlan_proto.unwrap_or_default().into();
            nm_vf.vlans = Some(vec![nm_vf_vlan]);
        }
        ret.push(nm_vf);
    }
    ret
}
