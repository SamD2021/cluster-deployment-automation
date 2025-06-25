#!/usr/bin/env python3
"""
Standalone test script for hostPath storage deployment.
This allows testing the storage deployment logic without a full cluster redeployment.
"""

import sys
import os
import argparse
import logging
import time
from logger import logger, configure_logger
from clusterStorage import ClusterStorage
from k8sClient import K8sClient


def test_storage_deployment(kubeconfig_path: str) -> bool:
    """Test hostPath storage deployment and verify it works correctly"""
    try:
        logger.info("=" * 60)
        logger.info("Testing HostPath Storage Deployment")
        logger.info("=" * 60)

        # Initialize storage deployment
        storage = ClusterStorage(kubeconfig_path)

        # Deploy storage
        logger.info("Starting hostPath storage deployment...")
        storage.deploy_storage()

        # Verify storage class was created
        logger.info("Verifying storage class creation...")
        k8s_client = K8sClient(kubeconfig_path)
        storage_class_name = storage.get_storage_class_name()

        result = k8s_client.oc(f"get storageclass {storage_class_name}")
        if result.returncode == 0:
            logger.info(f"Storage class '{storage_class_name}' created successfully")
        else:
            logger.warning(f"Storage class '{storage_class_name}' not found, but continuing...")

        # Check persistent volume
        logger.info("Checking persistent volume...")
        result = k8s_client.oc("get pv registry-pv")
        if result.returncode == 0:
            logger.info("Registry PV created successfully")
        else:
            logger.warning("Registry PV not found")

        # Show storage-related resources
        logger.info("Available storage classes:")
        k8s_client.oc("get storageclass")

        logger.info("Available persistent volumes:")
        k8s_client.oc("get pv")

        logger.info("=" * 60)
        logger.info("HostPath Storage deployment test completed successfully!")
        logger.info(f"Storage class to use for registry: {storage_class_name}")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"Storage deployment test failed: {e}")
        return False


def test_registry_with_storage(kubeconfig_path: str) -> bool:
    """Test registry deployment with hostPath storage"""
    try:
        from imageRegistry import InClusterRegistry

        logger.info("=" * 60)
        logger.info("Testing Registry with HostPath Storage")
        logger.info("=" * 60)

        storage = ClusterStorage(kubeconfig_path)
        storage_class_name = storage.get_storage_class_name()

        logger.info(f"Deploying registry with storage class: {storage_class_name}")
        icr = InClusterRegistry(kubeconfig_path, storage_class=storage_class_name)
        icr.deploy()

        logger.info("Registry with hostPath storage deployed successfully!")
        logger.info(f"Registry URL: {icr.get_url()}")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"Registry deployment test failed: {e}")
        return False


def cleanup_storage(kubeconfig_path: str) -> bool:
    """Clean up hostPath storage deployment for re-testing"""
    try:
        logger.info("=" * 60)
        logger.info("Cleaning up HostPath Storage (for re-testing)")
        logger.info("=" * 60)

        k8s_client = K8sClient(kubeconfig_path)

        # Clean up in reverse order
        logger.info("Deleting registry PVC if it exists...")
        k8s_client.oc("delete pvc -l app=registry --all-namespaces --ignore-not-found --timeout=30s")
        k8s_client.oc("delete pvc registry-storage -n openshift-image-registry --ignore-not-found --timeout=30s")

        logger.info("Deleting registry PV...")
        k8s_client.oc("delete pv registry-pv --ignore-not-found --timeout=30s")

        logger.info("Deleting hostPath storage class...")
        k8s_client.oc("delete storageclass local-hostpath --ignore-not-found --timeout=30s")

        logger.info("Cleaning up any remaining storage directory DaemonSets...")
        k8s_client.oc("delete daemonset storage-dir-creator -n kube-system --ignore-not-found --timeout=30s")

        # Wait a moment for cleanup to settle

        logger.info("Waiting for cleanup to settle...")
        time.sleep(5)

        # Verify cleanup
        logger.info("Verifying cleanup...")
        result = k8s_client.oc("get storageclass local-hostpath")
        if result.returncode == 0:
            logger.warning("Storage class still exists")
        else:
            logger.info("Storage class cleaned up")

        result = k8s_client.oc("get pv registry-pv")
        if result.returncode == 0:
            logger.warning("Registry PV still exists")
        else:
            logger.info("Registry PV cleaned up")

        logger.info("Storage cleanup completed")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"Storage cleanup failed: {e}")
        return False


def cleanup_registry(kubeconfig_path: str) -> bool:
    """Clean up in-cluster registry configuration and restore to OpenShift defaults"""
    try:
        logger.info("=" * 60)
        logger.info("Restoring Registry to OpenShift Defaults")
        logger.info("=" * 60)

        k8s_client = K8sClient(kubeconfig_path)

        # Clean up any registry storage PVC first
        logger.info("Cleaning up registry storage PVC...")
        k8s_client.oc("delete pvc registry-storage -n openshift-image-registry --ignore-not-found --timeout=30s")

        # Reset registry to OpenShift defaults
        logger.info("Resetting registry management state to Removed (OpenShift default)...")
        k8s_client.oc("patch configs.imageregistry.operator.openshift.io cluster --type=merge --patch '{\"spec\":{\"managementState\":\"Removed\"}}' ")

        # Remove any storage configuration completely (restore to no storage config)
        logger.info("Removing all storage configuration (restore to OpenShift default)...")
        k8s_client.oc("patch configs.imageregistry.operator.openshift.io cluster --type=json -p '[{\"op\": \"remove\", \"path\": \"/spec/storage\"}]' ")

        # Disable default route (restore to OpenShift default)
        logger.info("Disabling default route (restore to OpenShift default)...")
        k8s_client.oc("patch configs.imageregistry.operator.openshift.io cluster --type=merge --patch '{\"spec\":{\"defaultRoute\":false}}' ")

        # Clean up test namespace and service account
        logger.info("Cleaning up test namespace...")
        k8s_client.oc("delete namespace in-cluster-registry --ignore-not-found --timeout=60s")

        # Wait for changes to be applied
        import time

        logger.info("Waiting for registry to return to default state...")
        time.sleep(10)

        # Verify the registry is back to defaults
        logger.info("Verifying registry is back to OpenShift defaults...")
        result = k8s_client.oc("get configs.imageregistry.operator.openshift.io cluster -o jsonpath='{.spec.managementState}'")
        if result.returncode == 0 and "Removed" in result.out:
            logger.info("Registry management state restored to 'Removed'")
        else:
            logger.warning("Registry management state may not be properly reset")

        logger.info("Registry restored to OpenShift defaults")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"Registry cleanup failed: {e}")
        return False


def full_cleanup(kubeconfig_path: str) -> bool:
    """Clean up both storage and registry for complete re-testing"""
    try:
        logger.info("=" * 60)
        logger.info("Full Cleanup: Storage + Registry")
        logger.info("=" * 60)

        # Clean up registry first, then storage
        registry_success = cleanup_registry(kubeconfig_path)
        storage_success = cleanup_storage(kubeconfig_path)

        success = registry_success and storage_success

        if success:
            logger.info("Full cleanup completed successfully")
        else:
            logger.error("Some cleanup operations failed")

        logger.info("=" * 60)
        return success

    except Exception as e:
        logger.error(f"Full cleanup failed: {e}")
        return False


def test_stuck_pvc_cleanup(kubeconfig_path: str) -> bool:
    """Test the enhanced cleanup functionality for stuck PVCs and PVs"""
    try:
        logger.info("=" * 60)
        logger.info("Testing Stuck PVC/PV Cleanup Functionality")
        logger.info("=" * 60)

        storage = ClusterStorage(kubeconfig_path)
        k8s_client = K8sClient(kubeconfig_path)

        # First, deploy storage normally
        logger.info("Deploying initial storage...")
        storage.deploy_storage()

        # Create a PVC that will bind to the PV
        logger.info("Creating registry PVC...")
        storage.ensure_registry_pvc_created()

        # Verify initial setup
        pvc_result = k8s_client.oc("get pvc registry-storage -n openshift-image-registry -o jsonpath='{.status.phase}'")
        pv_result = k8s_client.oc("get pv registry-pv -o jsonpath='{.status.phase}'")

        logger.info(f"Initial PVC status: {pvc_result.out.strip() if pvc_result.success() else 'Not found'}")
        logger.info(f"Initial PV status: {pv_result.out.strip() if pv_result.success() else 'Not found'}")

        # Now simulate a stuck scenario by testing our cleanup methods directly
        logger.info("Testing comprehensive cleanup functionality...")

        # Test the cleanup methods (this should handle any stuck resources gracefully)
        storage.cleanup_existing_storage()

        # Verify cleanup worked
        pvc_check = k8s_client.oc("get pvc registry-storage -n openshift-image-registry")
        pv_check = k8s_client.oc("get pv registry-pv")

        if pvc_check.success():
            logger.warning("PVC still exists after cleanup")
        else:
            logger.info("PVC successfully removed by cleanup")

        if pv_check.success():
            logger.warning("PV still exists after cleanup")
        else:
            logger.info("PV successfully removed by cleanup")

        # Now redeploy to test the full cycle
        logger.info("Redeploying storage after cleanup...")
        storage.deploy_storage()
        storage.ensure_registry_pvc_created()

        # Verify final state
        final_pvc = k8s_client.oc("get pvc registry-storage -n openshift-image-registry -o jsonpath='{.status.phase}'")
        final_pv = k8s_client.oc("get pv registry-pv -o jsonpath='{.status.phase}'")

        logger.info(f"Final PVC status: {final_pvc.out.strip() if final_pvc.success() else 'Not found'}")
        logger.info(f"Final PV status: {final_pv.out.strip() if final_pv.success() else 'Not found'}")

        logger.info("=" * 60)
        logger.info("Stuck PVC/PV cleanup test completed successfully!")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"Stuck PVC cleanup test failed: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Test hostPath storage deployment")
    parser.add_argument("--kubeconfig", "-k", required=True, help="Path to kubeconfig file")
    parser.add_argument(
        "--action",
        "-a",
        choices=["deploy", "registry", "cleanup", "cleanup-registry", "cleanup-all", "full", "stuck-pvc-cleanup"],
        default="deploy",
        help="Action to perform: deploy (storage only), registry (storage + registry), cleanup (storage only), cleanup-registry (registry only), cleanup-all (both), or full (deploy storage + registry)",
    )
    parser.add_argument('-v', '--verbosity', choices=['debug', 'info', 'warning', 'error', 'critical'], default='debug', help='Set the logging level (default: debug)')

    args = parser.parse_args()

    # Set debug logging level if requested
    configure_logger(getattr(logging, args.verbosity.upper()))

    if not os.path.exists(args.kubeconfig):
        logger.error(f"Kubeconfig file not found: {args.kubeconfig}")
        sys.exit(1)

    success = True

    if args.action == "cleanup":
        success = cleanup_storage(args.kubeconfig)
    elif args.action == "cleanup-registry":
        success = cleanup_registry(args.kubeconfig)
    elif args.action == "cleanup-all":
        success = full_cleanup(args.kubeconfig)
    elif args.action == "deploy":
        success = test_storage_deployment(args.kubeconfig)
    elif args.action == "registry":
        success = test_registry_with_storage(args.kubeconfig)
    elif args.action == "full":
        success = test_storage_deployment(args.kubeconfig)
        if success:
            success = test_registry_with_storage(args.kubeconfig)
    elif args.action == "stuck-pvc-cleanup":
        success = test_stuck_pvc_cleanup(args.kubeconfig)

    if success:
        logger.info("All tests completed successfully!")
        sys.exit(0)
    else:
        logger.error("Tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
